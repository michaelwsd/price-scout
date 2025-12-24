import asyncio
from scraper import scrape_mpn_single
import streamlit as st

vendor_names = {
    "scorptec": "Scorptec Computers",
    "mwave": "Mwave Australia",
    "pc_case_gear": "PC Case Gear",
    "jw_computers": "JW Computers",
    "umart": "Umart"
}

st.set_page_config(page_title="Computer Parts Price Scout", layout="wide")
st.title("💻 Computer Parts Price Scout")

mpn_input = st.text_input("Enter MPN:", "")

if st.button("Fetch Prices") and mpn_input:
    with st.spinner(f"Fetching results for MPN: {mpn_input}..."):
        results = asyncio.run(scrape_mpn_single(mpn_input.strip()))

    # Layout: two columns for table + details
    st.subheader(f"Results for MPN: `{mpn_input}`")
    
    # Build table data
    table_data = []
    for res in results:
        table_data.append({
            "Vendor": vendor_names[res.vendor_id],
            "Price": f"{res.price} {res.currency}" if res.price else "Not Found",
            "MPN Found": "✅" if res.found else "❌",
            "URL": f"[Link]({res.url})" if res.url else "Not Found",
            "Scraped At": res.scraped_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    # Display main table
    st.table(table_data)

    # Show detailed info in expanders
    st.markdown("### Detailed Vendor Info")
    for res in results:
        with st.expander(f"{vendor_names[res.vendor_id]}"):
            st.markdown(f"**MPN:** {res.mpn or 'Not Found'}")
            st.markdown(f"**Price:** {res.price} {res.currency if res.price else ''}")
            st.markdown(f"**URL:** [{res.url}]({res.url})" if res.url else "Not Found")
            st.markdown(f"**Scraped At:** {res.scraped_at.strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown(f"**Found:** {'✅ Yes' if res.found else '❌ No'}")
