import pandas as pd
import streamlit as st

def compute_processing_order_by_asset_inventory(df: pd.DataFrame, starting_balances: dict = None, prompt_user=True) -> pd.DataFrame:
    results = []
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    if starting_balances is None:
        starting_balances = {}

    for (asset, inventory), group in df.groupby(['asset', 'inventory']):
        group = group.sort_values('timestamp').copy()
        group['process_order'] = -1

        if (asset, inventory) in starting_balances:
            start_balance = starting_balances[(asset, inventory)]
        elif prompt_user:
            start_balance = group.iloc[0]['assetBalance'] - group.iloc[0]['assetUnitAdj']
        else:
            start_balance = group.iloc[0]['assetBalance'] - group.iloc[0]['assetUnitAdj']

        unprocessed = group.copy()
        current_balance = start_balance
        order = []

        for i in range(len(group)):
            unprocessed['simulated_balance'] = current_balance + unprocessed['assetUnitAdj']
            unprocessed['diff'] = (unprocessed['simulated_balance'] - unprocessed['assetBalance']).abs()
            next_idx = unprocessed['diff'].idxmin()
            order.append((next_idx, i))
            current_balance += unprocessed.loc[next_idx, 'assetUnitAdj']
            unprocessed = unprocessed.drop(index=next_idx)

        for idx, proc_order in order:
            group.loc[idx, 'process_order'] = proc_order

        results.append(group)

    final_df = pd.concat(results).sort_values(['asset', 'inventory', 'process_order'])
    return final_df

# Streamlit App
st.title("Asset Inventory Report Processor")

uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    st.subheader("Step 1: Starting Balances")
    st.markdown("Please provide the starting balance per asset and per inventory. If left blank, the app will assume a starting balance of 0.")

    unique_pairs = df[['asset', 'inventory']].drop_duplicates().values
    starting_balances = {}
    for asset, inventory in unique_pairs:
        key = f"{asset} | {inventory}"
        user_input = st.text_input(f"Starting balance for {key}", value="0")
        try:
            starting_balances[(asset, inventory)] = float(user_input)
        except ValueError:
            st.warning(f"Invalid input for {key}. Defaulting to 0.")
            starting_balances[(asset, inventory)] = 0

    if st.button("Process Report"):
        processed_df = compute_processing_order_by_asset_inventory(df, starting_balances, prompt_user=False)

        st.success("Processing complete!")
        st.dataframe(processed_df)

        csv = processed_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Processed CSV",
            data=csv,
            file_name='processed_asset_inventory.csv',
            mime='text/csv'
        )
