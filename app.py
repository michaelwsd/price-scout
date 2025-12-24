import asyncio
import time
import csv
import pandas as pd
from io import StringIO
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

# Create tabs for single and batch processing
tab_single, tab_batch = st.tabs(["Single MPN Query", "CSV Batch Processing"])


# TAB 1: Single MPN Query
with tab_single:
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
                st.markdown(f"**Price:** {res.price} {res.currency if res.price else 'Not Found'}")
                st.markdown(f"**URL:** [{res.url}]({res.url})" if res.url else "**URL:** Not Found")
                st.markdown(f"**Scraped At:** {res.scraped_at.strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown(f"**Found:** {'✅' if res.found else '❌'}")

# TAB 2: CSV Batch Processing (New functionality)
with tab_batch:
    st.markdown("### Upload CSV file for batch processing")
    st.markdown("CSV file must contain a column named **'mpn'** or **'name'**")

    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

    if uploaded_file is not None:
        try:
            # Read CSV file
            content = uploaded_file.read().decode('utf-8')
            content_lines = content.splitlines()
            csv_reader = csv.DictReader(content_lines)

            # Check for mpn or name column
            mpn_column = None
            if 'mpn' in csv_reader.fieldnames:
                mpn_column = 'mpn'
            elif 'name' in csv_reader.fieldnames:
                mpn_column = 'name'
            else:
                st.error("❌ CSV file must contain 'mpn' or 'name' column")
                st.stop()

            # Extract MPNs
            csv_reader = csv.DictReader(content_lines)
            mpns = [row[mpn_column].strip() for row in csv_reader if row.get(mpn_column, '').strip()]

            st.success(f"✅ Loaded {len(mpns)} MPNs from CSV")

            with st.expander("Preview MPNs"):
                st.write(mpns[:10])
                if len(mpns) > 10:
                    st.write(f"... and {len(mpns) - 10} more")

            if st.button("Start Batch Processing", type="primary"):
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Batch processing
                start_time = time.time()
                all_results = []
                successful_count = 0

                for i, mpn in enumerate(mpns):
                    status_text.text(f"Processing {i+1}/{len(mpns)}: {mpn}")
                    progress_bar.progress((i + 1) / len(mpns))

                    # Scrape single MPN
                    results = asyncio.run(scrape_mpn_single(mpn))

                    # Store results with MPN
                    mpn_result = {'mpn': mpn}
                    lowest_price = None
                    lowest_vendor = None

                    for res in results:
                        vendor_key = res.vendor_id
                        if res.price is not None:
                            mpn_result[f'{vendor_key}_price'] = float(res.price)
                            mpn_result[f'{vendor_key}_url'] = str(res.url)

                            # Track lowest price
                            if lowest_price is None or res.price < lowest_price:
                                lowest_price = res.price
                                lowest_vendor = vendor_key
                        else:
                            mpn_result[f'{vendor_key}_price'] = None
                            mpn_result[f'{vendor_key}_url'] = None

                    mpn_result['lowest_price'] = float(lowest_price) if lowest_price else None
                    mpn_result['lowest_vendor'] = lowest_vendor

                    all_results.append(mpn_result)

                    if lowest_price is not None:
                        successful_count += 1

                elapsed_time = time.time() - start_time

                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()

                # Display summary statistics
                st.success("✅ Batch processing completed!")

                st.markdown("---")
                st.markdown("### 📊 Processing Summary")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total MPNs", len(mpns))
                with col2:
                    st.metric("Successfully Found", successful_count)
                with col3:
                    st.metric("Success Rate", f"{successful_count/len(mpns)*100:.1f}%")
                with col4:
                    st.metric("Total Time", f"{elapsed_time:.2f}s")

                st.markdown(f"**Average time per MPN:** {elapsed_time/len(mpns):.2f} seconds")

                # Display results table
                st.markdown("---")
                st.markdown("### 📋 Detailed Results")

                df_results = pd.DataFrame(all_results)
                st.dataframe(df_results, use_container_width=True)

                # Download button
                csv_output = df_results.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv_output,
                    file_name="batch_results.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"❌ Error processing CSV: {str(e)}")
