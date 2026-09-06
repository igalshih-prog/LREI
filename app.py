from pathlib import Path

import streamlit as st

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.statistics import LotteryStatistics


st.set_page_config(
    page_title="LREI Lottery",
    page_icon="🎯",
    layout="centered",
)


@st.cache_data
def load_lottery_data():
    root = Path(__file__).resolve().parent
    data_file = root / "data" / "lottery.csv"

    dataset = CsvDatasetLoader().load(data_file)
    statistics = LotteryStatistics.from_dataset(dataset)

    return dataset, statistics


def generate_tickets(ticket_count: int, seed: int):
    dataset, statistics = load_lottery_data()

    engine = RecommendationEngine()

    result = engine.recommend(
        statistics=statistics,
        ticket_count=50,
        seed=seed,
    )

    tickets = result.recommended_tickets_with_strong[:ticket_count]

    return dataset, result, tickets


st.title("🎯 LREI")
st.subheader("Lottery Recommendation Engine")

st.write(
    "ניתוח נתוני הגרלות והפקת טורים מומלצים "
    "באמצעות מנוע LREI."
)

st.divider()

ticket_count = st.selectbox(
    "מספר טורים",
    [10, 14],
    index=1,
)

seed = st.number_input(
    "Seed",
    min_value=0,
    value=42,
    step=1,
)

if st.button(
    "🎲 צור טורים",
    use_container_width=True,
    type="primary",
):
    with st.spinner("מייצר טורים..."):
        dataset, result, tickets = generate_tickets(
            ticket_count=ticket_count,
            seed=seed,
        )

    st.success("הטורים נוצרו בהצלחה!")

    st.metric(
        "הגרלות שנותחו",
        len(dataset),
    )

    st.metric(
        "טורים מומלצים",
        len(tickets),
    )

    st.divider()

    st.subheader("🎯 הטורים המומלצים")

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
        label="📋 הורד את הטורים",
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
