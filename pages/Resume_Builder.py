import streamlit as st

st.title("Resume Builder")
st.caption("Generate or tailor resumes for target jobs")

st.write("This is a placeholder page for resume builder.")

st.markdown("### Planned Inputs")
st.text_input("Target Role")
st.text_area("Paste Existing Resume Content")
st.button("Generate Draft Resume", type="primary")

st.info("Replace this placeholder with your generation pipeline and export actions.")
