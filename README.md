# README.md for Universal Milestone Timeline Viewer

# Universal Milestone Timeline Viewer

An advanced, interactive **Streamlit + Plotly** web app to visualize project milestones. Upload Excel/CSV files, map columns, and view **Contractual vs Actual/Anticipated** timelines with filters, KPI cards, and exports.

## ✨ Features

- **Upload Excel/CSV** files with flexible sheet and column mapping
- **Anchor options**: First date, *Notice to Proceed*, or custom
- **Granularity**: Monthly or quarterly timeline
- **Status engine**: On-Time, Early, Delayed, Pending, etc.
- **Rich UI**: Color themes, filters, search, today line
- **KPI cards**: Counts, on-time %, average delay/early
- **Group/category breakdown** (optional)
- **Export**: CSV, Excel, interactive HTML, PNG*
- **Modern look** with responsive Streamlit layout

\*PNG export requires [`kaleido`](https://github.com/plotly/Kaleido) installed.

## 📦 Requirements

- Python 3.11 (recommended)
- Packages listed in `requirements.txt`:
  ```text
  streamlit>=1.37
  pandas>=2.2
  plotly>=5.22
  numpy>=1.26
  openpyxl>=3.1
  xlrd>=2.0.1
  xlsxwriter>=3.2
  kaleido>=0.2.1
  ```

## 🚀 How to Run Locally

1. **Clone this repository**:
   ```bash
   git clone https://github.com/<your-username>/universal-timeline-viewer.git
   cd universal-timeline-viewer
   ```

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**:
   ```bash
   streamlit run app.py
   ```

5. Open the URL shown in your terminal (usually `http://localhost:8501`).

## 🌐 Deploy on Streamlit Cloud

1. Push your code to GitHub.
2. Go to [Streamlit Cloud](https://share.streamlit.io).
3. **New app** → select this repo → `main` branch → `app.py`.
4. Add `runtime.txt` with `3.11` to pin Python version.
5. Streamlit Cloud will install dependencies and deploy automatically.

## 📄 Usage Notes

- Excel file must have at least three columns:
  - **Milestone name** (e.g., “Boiler Hydrostatic Test”)
  - **Contractual/Baseline date**
  - **Actual/Anticipated date**
- Row named **“Notice to Proceed”** is recommended to auto-anchor the timeline.
- Missing dates are handled gracefully and shown as *Pending*.
- Sample template can be downloaded from the app.

## 🛠️ Customization

- Adjust colors and themes in the sidebar.
- Add groups or categories (e.g., Boiler, Electrical) to see breakdowns.
- Code is modular; functions like `_excel_engine_for()` handle file engines.
- Export chart and filtered data for reports.

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue to discuss what you’d like to change.

## 📜 License

MIT License © 2025 [Aayush Kumar]
