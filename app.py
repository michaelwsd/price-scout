import time
import asyncio
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

# --- PAGE CONFIG ---
st.set_page_config(page_title="Price Scout", page_icon="💻", layout="wide")

# Custom CSS for high-contrast dashboard elements
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    /* Custom Card Design */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border-top: 5px solid #1E88E5;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-label { font-size: 0.9rem; color: #555; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 1.8rem; color: #111; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# Helper function for custom metric cards
def render_custom_metric(label, value, border_color="#1E88E5"):
    st.markdown(f"""
        <div class="metric-card" style="border-top-color: {border_color};">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

st.title("💻 Computer Parts Price Scout")
st.divider()

tab_single, tab_batch = st.tabs(["🔍 Single MPN Query", "📁 CSV Batch Processing"])

# --- TAB 1: SINGLE QUERY (Logic kept same, UI polished) ---
with tab_single:
    col_input, _ = st.columns([2, 2])
    with col_input:
        mpn_input = st.text_input("Enter MPN:", placeholder="e.g. 12400F")

    if st.button("Fetch Prices", type="primary") and mpn_input:
        with st.spinner(f"Searching {mpn_input}..."):
            results = asyncio.run(scrape_mpn_single(mpn_input.strip()))
        
        df_single = pd.DataFrame([{
            "Vendor": vendor_names.get(res.vendor_id, res.vendor_id),
            "Price": float(res.price) if res.price else None,
            "Found": "✅" if res.found else "❌",
            "URL": str(res.url) if res.url else None
        } for res in results])

        st.dataframe(
            df_single,
            column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "URL": st.column_config.LinkColumn()},
            width='stretch', hide_index=True
        )

# --- TAB 2: BATCH PROCESSING ---
with tab_batch:
    st.markdown("### 📄 Upload & Manage Batch")
    uploaded_file = st.file_uploader("Upload CSV", type=['csv'])

    if uploaded_file is not None:
        if 'mpn_list' not in st.session_state:
            try:
                content = uploaded_file.read().decode('utf-8')
                df_upload = pd.read_csv(StringIO(content))
                col_to_use = next((c for c in ['mpn', 'name'] if c in df_upload.columns), None)
                
                if col_to_use:
                    st.session_state.mpn_list = df_upload[[col_to_use]].dropna().rename(columns={col_to_use: 'MPN To Process'})
                else:
                    st.error("❌ CSV must contain 'mpn' or 'name' column")
                    st.stop()
            except Exception as e:
                st.error(f"Error: {e}")

        if 'mpn_list' in st.session_state:
            edited_df = st.data_editor(st.session_state.mpn_list, width='stretch', num_rows="dynamic", key="mpn_editor")
            st.session_state.mpn_list = edited_df
            mpns_to_scan = edited_df['MPN To Process'].tolist()

            if st.button("🚀 Start Batch Search", type="primary"):
                progress_bar = st.progress(0)
                all_results = []
                successful_count = 0
                start_time = time.time()

                for i, mpn in enumerate(mpns_to_scan):
                    progress_bar.progress((i + 1) / len(mpns_to_scan))
                    results = asyncio.run(scrape_mpn_single(mpn))

                    mpn_result = {'MPN': mpn}
                    prices = [float(res.price) for res in results if res.price]
                    lowest_price = min(prices) if prices else None
                    
                    for res in results:
                        mpn_result[f'{vendor_names[res.vendor_id]} Price'] = float(res.price) if res.price else None

                    mpn_result['Best Price'] = lowest_price
                    if lowest_price: successful_count += 1
                    all_results.append(mpn_result)

                elapsed_time = time.time() - start_time
                success_rate = (successful_count/len(mpns_to_scan)*100)

                # --- NEW HIGH-CONTRAST SUMMARY DASHBOARD ---
                st.divider()
                st.subheader("📊 Processing Insights")
                c1, c2, c3, c4 = st.columns(4)
                with c1: render_custom_metric("Total Items", len(mpns_to_scan), "#1E88E5")
                with c2: render_custom_metric("Items Found", successful_count, "#43A047")
                with c3: 
                    rate_color = "#43A047" if success_rate > 80 else "#FB8C00"
                    render_custom_metric("Success Rate", f"{success_rate:.1f}%", rate_color)
                with c4: render_custom_metric("Time Taken", f"{elapsed_time:.1f}s", "#757575")

                # --- IMPROVED TABLE HIGHLIGHTING ---
                df_final = pd.DataFrame(all_results)
                
                # Reorder to put critical info at the front
                main_cols = ['MPN', 'Best Price']
                other_cols = [c for c in df_final.columns if c not in main_cols]
                df_final = df_final[main_cols + other_cols]

                def highlight_best_price(row):
                    styles = []
                    for col in row.index:
                        # Only apply to vendor price columns
                        if col.endswith('Price') and row[col] == row.get('Best Price'):
                            styles.append('background-color: #A7F3D0; color: #064E3B; font-weight: bold')
                        else:
                            styles.append('') # default
                    return styles

                st.markdown("### 📋 Comparative Results")
                st.dataframe(
                    df_final.style.apply(highlight_best_price, axis=1)
                            .format(precision=2, na_rep="-", subset=[c for c in df_final.columns if 'price' in c.lower()]),
                    width='stretch'
                )

                st.download_button("📥 Export Results", df_final.to_csv(index=False), "results.csv", "text/csv")