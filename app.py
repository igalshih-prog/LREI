from math import comb
from pathlib import Path
import tempfile

import streamlit as st

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.elite import EliteProRecommendationEngine
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.portfolio_coverage import portfolio_coverage
from lrei.lottery.smart import SmartRecommendationEngine
from lrei.lottery.coverage_engine import CoverageRecommendationEngine
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


def generate_smart_tickets(dataset, seed: int):
    engine = SmartRecommendationEngine()
    result = engine.recommend(dataset=dataset, seed=seed)
    tickets = result.recommended_tickets_with_strong[:14]
    return result, tickets


def generate_coverage_tickets(dataset, seed: int):
    engine = CoverageRecommendationEngine()
    result = engine.recommend(dataset=dataset, seed=seed)
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
    options=["Regular", "Pro", "Smart", "Coverage"],
    index=1,
    horizontal=True,
)

if mode == "Pro":
    st.info(
        "Pro משתמש בהרכב Ensemble של Rank, Raw Frequency ו-EWMA, "
        "צירופי זוגות ושלשות, פרופיל מבני ואופטימיזציה מקומית של 14 הטורים יחד."
    )
elif mode == "Smart":
    st.info(
        "Smart בוחר בין Regular, Pro ו-Elite לפי בדיקה היסטורית כרונולוגית, "
        "ואז מפיק 14 טורים. הבחירה מבוססת על ביצועי עבר ואינה מבטיחה חיזוי."
    )
elif mode == "Coverage":
    st.info(
        "Coverage מפיק 14 טורים ייחודיים שבהם כל זוג חולק לכל היותר מספר ראשי אחד. "
        "כך מתקבל הכיסוי התאורטי המרבי לסיכוי של לפחות 4 מתוך 6 במספרים הראשיים. "
        "המצב אינו חוזה את ההגרלה ואינו מגדיל את סיכוי הג׳קפוט מעל הסיכוי התאורטי של 14 טורים."
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
        if mode == "Smart":
            result, tickets = generate_smart_tickets(
                dataset=dataset,
                seed=seed,
            )
        elif mode == "Coverage":
            result, tickets = generate_coverage_tickets(
                dataset=dataset,
                seed=seed,
            )
        elif mode == "Pro":
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

    with st.expander("📐 כיסוי מתמטי של 14 הטורים", expanded=False):
        main_tickets = [ticket.numbers for ticket in tickets]
        coverage_4 = portfolio_coverage(main_tickets, threshold=4)["probability"]
        coverage_5 = portfolio_coverage(main_tickets, threshold=5)["probability"]
        coverage_6 = portfolio_coverage(main_tickets, threshold=6)["probability"]
        full_jackpot_probability = 14 / (comb(37, 6) * 7)

        coverage_columns = st.columns(3)
        coverage_columns[0].metric("לפחות 4/6 במספרים הראשיים", f"{coverage_4:.3%}")
        coverage_columns[1].metric("לפחות 5/6 במספרים הראשיים", f"{coverage_5:.3%}")
        coverage_columns[2].metric("6/6 במספרים הראשיים", f"{coverage_6:.5%}")
        st.caption(
            "הכיסוי מחושב בדיוק מול כל צירופי 6/37 האפשריים, ומתייחס למספרים הראשיים בלבד. "
            "הוא אינו תחזית לתוצאה הבאה. בהנחת הגרלה הוגנת וטורים ייחודיים, "
            f"סיכוי הג׳קפוט המלא ב־14 טורים הוא 1 ל־{1 / full_jackpot_probability:,.0f}, "
            "כולל המספר החזק; בחירת מספרים היסטוריים אינה משנה את הסיכוי התאורטי הזה."
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
