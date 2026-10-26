import streamlit as st

st.title("study-buddy")

pdf = st.file_uploader("강의 PDF를 올려 주세요", type="pdf")

if pdf:
    st.write("업로드 완료:", pdf.name)
    if st.button("정리본 만들기"):
        st.write("여기에 정리본이 나올 예정")