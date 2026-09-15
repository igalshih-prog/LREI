```python
from io import BytesIO
from pathlib import Path
import tempfile

import streamlit as st

from lrei.lottery.dataset import CsvDatasetLoader
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


def generate_tickets(
    dataset,
    ticket_count: int,
    seed: int,
):
    statistics = LotteryStatistics.from_dataset(dataset)
    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=statistics,
        ticket_count=50,
        seed=seed,
    )

    tickets = result.recommended_tickets_with_strong[:ticket_count]

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

seed = st.number_input(
    "Seed",
    min_value=0,
    value=42,
    step=1,
)

if st.button(
    "🎲 צור 14 טורים",
    use_container_width=True,
    type="primary",
):
    with st.spinner("מנתח את ההגרלות ומייצר טורים..."):
        result, tickets = generate_tickets(
            dataset=dataset,
            ticket_count=14,
            seed=seed,
        )

    st.success("14 הטורים נוצרו בהצלחה!")

    st.metric(
        "הגרלות שנותחו",
        len(dataset),
    )

    st.metric(
        "טורים מומלצים",
        len(tickets),
    )

    st.divider()

    st.subheader("🎯 14 הטורים המומלצים")

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

    for score in result.scores[:10]:
        st.write(
            f"Number {score.number:02d} — "
            f"{score.score:.6f}"
        )

    st.subheader("⭐ Strong Number Scores")

    for score in result.strong_scores[:7]:
        st.write(
            f"Strong {score.number:02d} — "
            f"{score.score:.6f}"
        )
```
