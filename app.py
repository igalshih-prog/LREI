from io import BytesIO
from pathlib import Path
import tempfile

import streamlit as st

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.elite import EliteProRecommendationEngine
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.statistics import LotteryStatistics


st.set_page_config(
    page_title="LREI Lottery",
    page_icon="🎯",
    layout="centered",
)


def load_dataset_from_file(file_bytes: bytes):
    with tempfile.NamedTemporaryFile(
        suffix=".csv",
        delete=False,
    ) as temp_file:
        temp_file.write(file_bytes)
        temp_path = Path(temp_file.name)

    try:
        dataset = CsvDatasetLoader().load(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)

    return dataset


@st.cache_data
def load_default_lottery_data():
    root = Path(__file__).resolve().parent
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    return dataset, statistics


def generate_regular_tickets(dataset, seed: int):
    statistics = LotteryStatistics.from_dataset(dataset)
    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=statistics,
        ticket_count=800,
        seed=seed,
    )

    tickets = result.recommended_tickets_with_strong[:14]

    return result, tickets


def generate_pro_tickets(dataset, seed: int):
    engine = EliteProRecommendationEngine()
    result = engine.recommend(
        dataset=dataset,
        seed=seed,
    )

    tickets = result.recommended_tickets_with_strong[:14]

    return result, tickets


st.title("🎯 LREI")
st.subheader("Lottery Recommendation Engine")

st.write(
    "ניתוח נתוני הגרלות והפקת טורים מומלצים "
    "באמצעות מנוע LREI."
)

st.divider()

st.subheader("📂 נתוני ההגרלות")

uploaded_file = st.file_uploader(
    "העלה קובץ CSV של ההגרלות",
    type=["csv"],
    help="מומלץ להעלות קובץ המכיל את 10 השנים האחרונות.",
)

if uploaded_file is not None:
    try:
        dataset = load_dataset_from_file(
            uploaded_file.getvalue()
        )

        st.success(
            f"הקובץ נטען בהצלחה — "
            f"{len(dataset)} הגרלות נותחו."
        )

    except Exception as error:
        st.error(
            "לא ניתן לטעון את הקובץ. "
            f"בדוק שהמבנה שלו מתאים לקובץ ההגרלות הקיים.\n\n"
            f"שגיאה: {error}"
        )
        st.stop()

else:
    dataset, _ = load_default_lottery_data()

    st.info(
        f"משתמש בנתוני ההגרלות הקיימים — "
        f"{len(dataset)} הגרלות."
    )

st.divider()

st.metric(
    "הגרלות זמינות לניתוח",
    len(dataset),
)

mode = st.radio(
    "בחר מנוע",
    options=["Regular", "Pro"],
    index=1,
    horizontal=True,
)

if mode == "Pro":
    st.info(
        "Pro משתמש בהרכב Ensemble של Rank, Raw Frequency ו-EWMA, "
        "צירופי זוגות ושלשות, פרופיל מבני ואופטימיזציה מקומית של 14 הטורים יחד."
    )
else:
    st.info(
        "Regular משתמש במנוע הבסיסי של LREI ומפיק 14 טורים."
    )

seed = st.number_input(
    "Seed",
    min_value=0,
    value=42,
    step=1,
)

if st.button(
    f"🎲 צור 14 טורים — {mode}",
    use_container_width=True,
    type="primary",
):
    with st.spinner(
        "מנתח את ההגרלות ומייצר טורים..."
    ):
        if mode == "Pro":
            result, tickets = generate_pro_tickets(
                dataset=dataset,
                seed=seed,
            )
        else:
            result, tickets = generate_regular_tickets(
                dataset=dataset,
                seed=seed,
            )

    st.success(
        f"14 הטורים נוצרו בהצלחה — {mode}!"
    )

    st.metric(
        "הגרלות שנותחו",
        len(dataset),
    )

    st.metric(
        "טורים מומלצים",
        len(tickets),
    )

    st.divider()

    st.subheader(
        f"🎯 14 הטורים המומלצים — {mode}"
    )

    all_tickets = []

    for index, ticket in enumerate(tickets, start=1):
        numbers = " - ".join(
            f"{number:02d}"
            for number in sorted(ticket.numbers)
        )

        if ticket.strong_number is not None:
            text = (
                f"**טור {index:02d}:** "
                f"{numbers} "
                f"| ⭐ Strong: {ticket.strong_number}"
            )
        else:
            text = (
                f"**טור {index:02d}:** "
                f"{numbers}"
            )

        st.markdown(text)

        if ticket.strong_number is not None:
            all_tickets.append(
                f"Ticket {index:02d}: "
                f"{numbers} "
                f"| Strong: {ticket.strong_number}"
            )
        else:
            all_tickets.append(
                f"Ticket {index:02d}: {numbers}"
            )

    st.divider()

    st.download_button(
        label="📋 הורד את 14 הטורים",
        data="\n".join(all_tickets),
        file_name="lrei_tickets.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.divider()

    st.subheader("📊 Top Number Scores")

    for score in sorted(
        result.scores,
        key=lambda item: (-item.score, item.number),
    )[:10]:
        st.write(
            f"Number {score.number:02d} — "
            f"{score.score:.6f}"
        )

    st.subheader("⭐ Strong Number Scores")

    for score in sorted(
        result.strong_scores,
        key=lambda item: (-item.score, item.number),
    )[:7]:
        st.write(
            f"Strong {score.number:02d} — "
            f"{score.score:.6f}"
        )
