import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="구글매출정산변환",
    page_icon="📊",
    layout="centered"
)

st.title("📊 구글매출정산변환")
st.caption("대용량 Google Play 매출 정산 CSV 파일을 조각 단위로 읽어 Excel 파일로 변환합니다.")

st.warning(
    "Streamlit Cloud 기본 업로드 제한은 보통 200MB입니다. "
    "아래 설정 파일(config.toml)을 같이 올리면 500MB까지 업로드 가능하도록 설정합니다."
)

st.markdown("### 1. CSV 파일 업로드")
uploaded_file = st.file_uploader(
    "PlayApps.csv 파일을 업로드하세요",
    type=["csv"]
)

CHUNKSIZE = 100_000

GROUP_COLS_BASE = [
    "Buyer Country",
    "Sku Id",
    "Transaction Date",
    "Tax Type",
    "Product Title",
    "Transaction Type",
]

SUM_COLS = [
    "Amount (Buyer Currency)",
    "Amount (Merchant Currency)",
]

def convert_google_sales_large(file):
    aggregated_parts = []
    product_id_col_final = None

    reader = pd.read_csv(
        file,
        delimiter=",",
        keep_default_na=False,
        low_memory=False,
        chunksize=CHUNKSIZE
    )

    progress = st.progress(0)
    status = st.empty()

    for i, chunk in enumerate(reader, start=1):
        status.write(f"{i}번째 데이터 조각 처리 중...")

        if "Product id" in chunk.columns:
            product_id_col = "Product id"
        elif "Package ID" in chunk.columns:
            product_id_col = "Package ID"
        else:
            raise KeyError("CSV에서 'Product id' 또는 'Package ID' 컬럼을 찾을 수 없습니다.")

        product_id_col_final = product_id_col

        group_cols = GROUP_COLS_BASE.copy()
        group_cols.insert(5, product_id_col)

        required_cols = group_cols + SUM_COLS
        missing_cols = [col for col in required_cols if col not in chunk.columns]
        if missing_cols:
            raise KeyError("CSV에 필요한 컬럼이 없습니다: " + ", ".join(missing_cols))

        chunk = chunk[required_cols].copy()

        for col in SUM_COLS:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce").fillna(0)

        part = chunk.groupby(group_cols, as_index=False)[SUM_COLS].sum()
        aggregated_parts.append(part)

        # 총 row 수를 모르므로 진행률은 조각 개수 기준으로 임시 표시
        progress.progress(min(i * 5, 95))

    if not aggregated_parts:
        raise ValueError("처리할 데이터가 없습니다.")

    status.write("최종 집계 중...")

    combined = pd.concat(aggregated_parts, ignore_index=True)

    final_group_cols = GROUP_COLS_BASE.copy()
    final_group_cols.insert(5, product_id_col_final)

    result = combined.groupby(final_group_cols, as_index=False)[SUM_COLS].sum()

    progress.progress(100)
    status.write("처리 완료")

    return result

def dataframe_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="GoogleSales")
        workbook = writer.book
        worksheet = writer.sheets["GoogleSales"]

        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#D9EAF7",
            "border": 1
        })

        number_format = workbook.add_format({
            "num_format": "#,##0.00"
        })

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            width = max(12, min(45, len(str(value)) + 4))
            worksheet.set_column(col_num, col_num, width)

        for col_name in SUM_COLS:
            if col_name in df.columns:
                col_idx = df.columns.get_loc(col_name)
                worksheet.set_column(col_idx, col_idx, 22, number_format)

    return output.getvalue()

if uploaded_file is not None:
    try:
        st.markdown("### 2. 변환 결과")
        with st.spinner("대용량 파일 처리 중입니다. 잠시 기다려주세요."):
            result_df = convert_google_sales_large(uploaded_file)

        st.success("변환이 완료되었습니다.")
        st.write(f"결과 행 수: {len(result_df):,}행")
        st.dataframe(result_df.head(1000), use_container_width=True)
        st.caption("화면에는 최대 1,000행만 미리보기로 표시됩니다. 다운로드 파일에는 전체 결과가 포함됩니다.")

        excel_data = dataframe_to_excel_bytes(result_df)

        st.markdown("### 3. Excel 다운로드")
        st.download_button(
            label="📥 변환된 Excel 다운로드",
            data=excel_data,
            file_name="GoogleSales_out.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"처리 중 오류가 발생했습니다: {e}")
else:
    st.info("CSV 파일을 업로드하면 변환 결과와 다운로드 버튼이 표시됩니다.")
