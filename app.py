import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="구글매출정산변환",
    page_icon="📊",
    layout="centered"
)

st.title("📊 구글매출정산변환")
st.caption("Google Play 매출 정산 CSV 파일을 업로드하면 집계 후 Excel 파일로 변환합니다.")

st.markdown("### 1. CSV 파일 업로드")
uploaded_file = st.file_uploader(
    "PlayApps.csv 파일을 업로드하세요",
    type=["csv"]
)

def convert_google_sales(file):
    csv_t = pd.read_csv(
        file,
        delimiter=",",
        keep_default_na=False,
        low_memory=False
    )

    if "Product id" in csv_t.columns:
        product_id_col = "Product id"
    elif "Package ID" in csv_t.columns:
        product_id_col = "Package ID"
    else:
        raise KeyError("CSV에서 'Product id' 또는 'Package ID' 컬럼을 찾을 수 없습니다.")

    select_cols = [
        "Buyer Country",
        "Tax Type",
        "Sku Id",
        "Transaction Date",
        "Product Title",
        product_id_col,
        "Transaction Type",
        "Amount (Buyer Currency)",
        "Amount (Merchant Currency)",
    ]

    missing_cols = [col for col in select_cols if col not in csv_t.columns]
    if missing_cols:
        raise KeyError("CSV에 필요한 컬럼이 없습니다: " + ", ".join(missing_cols))

    csv_t2 = csv_t[select_cols]

    result = csv_t2.groupby(
        [
            "Buyer Country",
            "Sku Id",
            "Transaction Date",
            "Tax Type",
            "Product Title",
            product_id_col,
            "Transaction Type",
        ],
        as_index=False
    )[["Amount (Buyer Currency)", "Amount (Merchant Currency)"]].sum()

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

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            width = max(12, min(40, len(str(value)) + 4))
            worksheet.set_column(col_num, col_num, width)

    return output.getvalue()

if uploaded_file is not None:
    try:
        st.markdown("### 2. 변환 결과 미리보기")
        result_df = convert_google_sales(uploaded_file)

        st.success("변환이 완료되었습니다.")
        st.dataframe(result_df, use_container_width=True)

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
