from math import comb
from pathlib import Path
import tempfile

import streamlit as st

from lrei.lottery.dataset import CsvDatasetLoader
from lrei.lottery.dataset_freshness import inspect_freshness
from lrei.lottery.elite import EliteProRecommendationEngine
from lrei.lottery.recommendation import RecommendationEngine
from lrei.lottery.portfolio_coverage import portfolio_coverage
from lrei.lottery.any_prize_coverage_engine import AnyPrizeCoverageRecommendationEngine
from lrei.lottery.smart import SmartConfig, SmartRecommendationEngine
from lrei.lottery.coverage_engine import CoverageRecommendationEngine
from lrei.lottery.five_plus import five_plus_metrics
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


def generate_smart_tickets(
    dataset, seed: int, objective: str = "historical", selection_metric: str = "mean"
):
    engine = SmartRecommendationEngine(
        SmartConfig(objective=objective, selection_metric=selection_metric)
    )
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

# A valid user upload is never proof of first-party provenance. This UI
# runs research-only, regardless of draw-date freshness or green code CI.
research_warning = (
    "⚠️ NO PLAY — מחקר וניסוי על נייר בלבד. "
    "הקובץ שמוצג כאן לא עבר אימות מקור רשמי ופרוטוקולים מחייבים; "
    "בדיקות קוד תקינות ותאריך הגרלה עדכני אינם אישור להימור או יתרון חיזוי."
)
try:
    readiness = inspect_freshness(dataset)
except ValueError:
    research_warning += " לא ניתן לאמת את תאריך ההגרלה האחרונה בקובץ."
else:
    if readiness["status"] == "stale_dataset":
        research_warning += (
            f" ההגרלה האחרונה בקובץ: {readiness['latest_draw_id']} "
            f"({readiness['latest_draw_date_israel']}), "
            f"לפני {readiness['age_days']} ימים — מעבר למגבלת "
            f"{readiness['max_age_days']} ימים."
        )
    elif readiness["status"] == "future_dated_dataset":
        research_warning += " נמצא תאריך הגרלה עתידי בקובץ; הנתונים אינם מאושרים."

st.warning(research_warning)

st.divider()

st.metric(
    "הגרלות זמינות לניתוח",
    len(dataset),
)

mode = st.radio(
    "בחר מנוע",
    options=["Regular", "Pro", "Smart", "Coverage"],
    index=2,
    horizontal=True,
)

smart_objective = "historical"
if mode == "Pro":
    st.info(
        "Pro משתמש בהרכב Ensemble של Rank, Raw Frequency ו-EWMA, "
        "צירופי זוגות ושלשות, פרופיל מבני ואופטימיזציה מקומית של 14 הטורים יחד."
    )
elif mode == "Smart":
    objective_label = st.selectbox(
        "מה מטרת ההמלצה?",
        options=[
            "מקסום כיסוי ל־5+ (וגם 4+) — 14 טורים",
            "מקסום כיסוי ל־4+ במספרים הראשיים",
            "מקסום הסיכוי לזכייה כלשהי (3+ ראשיים)",
            "בחירה לפי ממוצע התאמות היסטורי",
            "ניסוי: בחירה לפי מדרגת הפרס ההיסטורית",
        ],
        index=0,
    )
    if objective_label == "מקסום כיסוי ל־5+ (וגם 4+) — 14 טורים":
        smart_objective = "coverage_5plus"
    elif objective_label == "מקסום כיסוי ל־4+ במספרים הראשיים":
        smart_objective = "coverage_4plus"
    elif objective_label == "מקסום הסיכוי לזכייה כלשהי (3+ ראשיים)":
        smart_objective = "coverage_any_prize"
    else:
        smart_objective = "historical"
    smart_selection_metric = (
        "prize"
        if objective_label == "ניסוי: בחירה לפי מדרגת הפרס ההיסטורית"
        else "mean"
    )
    if smart_objective == "coverage_5plus":
        st.info(
            "Smart 5+ מפעיל את אותו מנוע אופטימלי של Smart 4+: "
            "14 טורים שונים, עם חפיפה מרבית של מספר ראשי אחד בין כל שני טורים. "
            "הדבר ממקסם במקביל גם כיסוי 4+ וגם כיסוי 5+. "
            "הסיכוי המרבי לפגיעה ב־5 או 6 מספרים ראשיים הוא כ־0.1126% "
            "(1 ל־888 להגרלה). זו תקרה מתמטית, לא הבטחה או חיזוי."
        )
    elif smart_objective == "coverage_4plus":
        st.info(
            "Smart משתמש בכיסוי מתמטי: 14 טורים ייחודיים שבהם כל זוג חולק לכל היותר מספר ראשי אחד. "
            "כך ממקסמים את הסיכוי שלפחות טור אחד יפגע ב־4 מתוך 6 מספרים ראשיים. "
            "סיכוי הג׳קפוט נשאר זהה לכל קבוצה של 14 טורים ייחודיים."
        )
    elif smart_objective == "coverage_any_prize":
        st.info(
            "Smart בונה מאגר של טורים אקראיים תקינים ומחשב במדויק אילו תוצאות מתוך כל "
            "2,324,784 צירופי 6/37 נותנות לפחות 3 התאמות ראשיות. לאחר מכן הוא בוחר בגרידיות "
            "14 טורים שמוסיפים כמה שיותר תוצאות חדשות לכיסוי. זהו קירוב מתוך מאגר מועמדים, "
            "לא אופטימום גלובלי ולא חיזוי של המספרים. סיכוי הג׳קפוט נשאר זהה לכל קבוצה "
            "של 14 טורים ייחודיים."
        )
    elif smart_selection_metric == "prize":
        st.info(
            "ניסוי: Smart בוחר בין Regular, Pro ו-Elite לפי ניקוד מדרגת הפרס הטובה ביותר "
            "בכל הגרלת עבר: 1.0 לפרס ראשון, ניקוד יורד עד 0.125 לפרס שמיני, ו־0 ללא זכייה. "
            "הניקוד אינו אומדן כספי; המדד עלול להיות רועש ואינו תחזית לזכייה הבאה."
        )
    else:
        st.info(
            "Smart בוחר בין Regular, Pro ו-Elite לפי ממוצע התאמות בבדיקה היסטורית כרונולוגית, "
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
                objective=smart_objective,
                selection_metric=smart_selection_metric,
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
        # Use the exact bitmap path instead of materializing large Python sets.
        coverage_3 = AnyPrizeCoverageRecommendationEngine.coverage_probability(main_tickets)
        coverage_4 = portfolio_coverage(main_tickets, threshold=4)["probability"]
        five_metrics = five_plus_metrics(main_tickets)
        coverage_5 = five_metrics["probability"]
        coverage_6 = portfolio_coverage(main_tickets, threshold=6)["probability"]
        full_jackpot_probability = 14 / (comb(37, 6) * 7)

        coverage_columns = st.columns(4)
        coverage_columns[0].metric("לפחות 3/6 — כל זכייה", f"{coverage_3:.2%}")
        coverage_columns[1].metric("לפחות 4/6 ראשיים", f"{coverage_4:.3%}")
        coverage_columns[2].metric("לפחות 5/6 ראשיים", f"{coverage_5:.4%}")
        coverage_columns[3].metric("6/6 ראשיים", f"{coverage_6:.5%}")
        if five_metrics["is_optimal"]:
            st.metric(
                "לפחות 5 מספרים ראשיים + מספר חזק",
                f"{five_metrics['with_matching_strong_probability']:.4%}",
                help="כ־1 ל־6,216. מדובר במספר החזק הנכון בנוסף ל־5 או 6 מספרים ראשיים.",
            )
            st.success(
                "כיסוי 5+ הגיע למקסימום המתמטי של 14 טורים: "
                f"{five_metrics['probability']:.4%} (1 ל־888). "
                "אין אפשרות להבטיח 5 מספרים בהגרלה הבאה."
            )
        st.caption(
            "הכיסוי מחושב בדיוק מול כל צירופי 6/37 האפשריים. לפחות 3 מספרים ראשיים "
            "מזכים בפרס כלשהו לפי כללי הלוטו; המספר החזק קובע אם זו רמת פרס גבוהה יותר. "
            "המדדים הם הסתברויות תאורטיות להגרלה הוגנת, לא תחזית. "
            f"סיכוי הג׳קפוט המלא ב־14 טורים ייחודיים הוא 1 ל־{1 / full_jackpot_probability:,.0f}, "
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

    if mode == "Smart" and smart_objective in {
        "coverage_any_prize", "coverage_4plus", "coverage_5plus"
    }:
        st.subheader("📊 ציוני מספרים")
        st.caption(
            "במצבי הכיסוי 3+/4+/5+ אין דירוג ניבוי אמין למספרים הראשיים "
            "או למספר החזק. המערכת מפזרת את הטורים כדי למקסם את מדד הכיסוי "
            "המתמטי הנבחר, ואינה יודעת לחזות את המספרים בהגרלה הבאה."
        )
    else:
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
