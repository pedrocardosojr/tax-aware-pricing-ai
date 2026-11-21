"""Visual identity for the Streamlit preview, using native widgets."""

CSS = """
<style>
.stApp {
  --ink: #192844;
  --muted: #52617C;
  --indigo: #354BB5;
  --line: #DDE5F2;
  background: linear-gradient(148deg, #EAF0FF 0, #F4F6FC 27rem, #F4F6FC 100%);
}
[data-testid="stHeader"] {background: transparent;}
.block-container {max-width: 1320px; padding-top: 3.5rem; padding-bottom: 3rem;}
h1, h2, h3, h4 {color: var(--ink); letter-spacing: -.025em;}
h1 {font-size: clamp(1.85rem, 3.7vw, 2.85rem) !important; line-height: 1.12 !important;}
.lead {font-size: 1.06rem; color: var(--muted); margin: -.2rem 0 .5rem;}
[data-testid="stForm"] {border: 0;}
.st-key-intro_hero, .st-key-scenario_intro {max-width: 850px; margin: 0 auto;}
.st-key-intro_hero {margin: .55rem auto .8rem; gap: .45rem;}
.st-key-intro_hero h1 {padding: .35rem 0 .4rem;}
.st-key-intro_hero [data-testid="stImage"] {margin-bottom: .3rem;}
.st-key-masthead {margin-bottom: .7rem;}
.st-key-masthead img {max-height: 55px; width: auto;}
.st-key-scenario_intro, .st-key-market_panel, .st-key-ask_box {
  background: white;
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 7px 24px rgba(40, 58, 111, .065);
}
.st-key-scenario_intro {border-top: 4px solid var(--indigo); gap: .25rem;}
.st-key-product_fields, .st-key-analysis_fields, [data-testid="stForm"] {
  padding: .55rem .85rem .7rem;
}
.st-key-product_fields, .st-key-analysis_fields,
[data-testid="stForm"] > [data-testid="stVerticalBlock"] {gap: .45rem;}
.st-key-analysis_fields, [data-testid="stForm"] {
  border-top: 1px solid var(--line);
  border-radius: 0;
}
.st-key-scenario_intro .react-aria-ComboBox > div:has(input[role="combobox"]),
.st-key-scenario_intro [data-testid="stNumberInputContainer"] {
  background: #F5F7FC; border-color: var(--line);
}
.st-key-scenario_submit {
  padding: .45rem .65rem .55rem;
  border-radius: 10px;
  background: #F0F3FD;
  gap: .45rem;
}
[data-testid="stFormSubmitButton"] button {min-height: 2.65rem;}
[data-testid="stFormSubmitButton"] button:disabled {
  background: #E2E8F8; border-color: #D4DDF1; color: #4C5C79;
}
.st-key-market_panel {border-top: 3px solid #8093D8;}
.st-key-market_panel h3 {padding-top: .1rem;}
.market-legend {display:flex; flex-wrap:wrap; gap:.35rem 1rem; color:var(--muted); font-size:.88rem;}
.market-legend span {display:inline-flex; align-items:center; gap:.35rem;}
.market-legend i {display:inline-block; width:1.4rem;}
.market-own {border-top:2px dashed #354BB5;}
.market-median {border-top:2px dotted #62508B;}
.st-key-price_simulator [data-testid="stSliderThumbValue"],
.st-key-price_simulator [data-testid="stSliderTickBar"] {display:none;}
.market-band {height:.58rem; background:#D7DFF8; border:1px solid #7486C0; border-radius:2px;}
.market-legend .market-observed {background:#7486C0; width:.58rem; height:.58rem; border-radius:50%;}

.st-key-scenario_intro [data-testid="stVerticalBlockBorderWrapper"],
.st-key-market_panel [data-testid="stVerticalBlockBorderWrapper"],
.st-key-ask_box [data-testid="stVerticalBlockBorderWrapper"] {border: 0; padding: .2rem;}
.st-key-margin_gain, .st-key-margin_loss, .st-key-market_kpi, .st-key-tax_kpi {
  min-height: 10.5rem;
  border-radius: 14px;
  border: 1px solid var(--line);
  border-top: 4px solid var(--accent);
  background: var(--card);
}
.st-key-margin_gain {--accent: #08715D; --card: #EAF7F2;}
.st-key-margin_loss {--accent: #A83B4B; --card: #FFF0F2;}
.st-key-market_kpi {--accent: #354BB5; --card: #EDF1FF;}
.st-key-tax_kpi {--accent: #85510D; --card: #FFF6E8;}
[data-testid="stMetricValue"] {font-size: 1.9rem; color: var(--ink); letter-spacing: -.035em;}
[data-testid="stMetricLabel"] {font-size: .9rem; color: var(--muted);}
.st-key-margin_gain [data-testid="stMetricValue"], .st-key-margin_loss [data-testid="stMetricValue"],
.st-key-market_kpi [data-testid="stMetricValue"], .st-key-tax_kpi [data-testid="stMetricValue"] {
  color: var(--accent); font-size: clamp(1.5rem, 2.6vw, 2.25rem); font-weight: 730;
}
.st-key-summary_box, .st-key-answer_box {
  border: 1px solid #DFE7FB;
  border-radius: 14px;
  background: #F0F3FF;
}
.st-key-summary_box {border-left: 4px solid var(--indigo);}
.st-key-summary_box ul {margin-bottom: .25rem;}
.st-key-summary_box li {padding: .14rem 0;}
.st-key-price_simulator {
  border: 1px solid #CBD6F6;
  border-radius: 14px;
  border-top: 3px solid var(--indigo);
  background: #F0F3FF;
}
.st-key-ask_box button {border-color: #D4DCF3; background: #F5F7FF;}
.st-key-ask_box button:hover {border-color: var(--indigo); color: var(--indigo);}
.st-key-simulation_box {border-left: 4px solid var(--indigo);}
.st-key-insight_event, .st-key-insight_month, .st-key-insight_climate {
  min-height: 8.5rem;
  border-top: 3px solid #8093D8;
}
.forecast-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(4.5rem,1fr)); gap:.45rem;}
.forecast-day {text-align:center; background:#F4F6FC; border:1px solid var(--line);
  border-radius:10px; padding:.45rem .2rem; min-width:4.2rem;}
.fd-name, .fd-temp {font-weight:700; color:var(--ink);}
.fd-name {text-transform:capitalize; font-size:.85rem;}
.fd-temp {font-size:.92rem;}
.fd-date, .fd-rain {font-size:.74rem; color:var(--muted);}
.fd-temp b {color:var(--indigo);}
@media (max-width: 640px) {
  .block-container {padding-top: 2.8rem;}
  .st-key-intro_hero {margin-top: .5rem;}
  .st-key-product_fields, .st-key-analysis_fields, [data-testid="stForm"] {
    padding-inline: .4rem;
  }
  .st-key-intro_hero [data-testid="stImage"] {max-width: 300px;}
  .st-key-masthead [data-testid="stImage"] {max-width: 250px;}
  .st-key-margin_gain, .st-key-margin_loss, .st-key-market_kpi, .st-key-tax_kpi {min-height: 0;}
  [data-testid="stMetricValue"] {white-space: normal;}
  .js-plotly-plot .heatmap-label {display:none;}
}
</style>
"""
