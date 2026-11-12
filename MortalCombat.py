import streamlit as st

# This MUST be the first Streamlit command
st.set_page_config(page_title="Survival Calculator", layout="wide")

# Now import other libraries
import torch
import numpy as np
import joblib
import pandas as pd
import matplotlib.pyplot as plt
from pycox.models import CoxPH
import torch.nn as nn
import torchtuples as tt


def seed_everything(seed=42):
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# Initialize model architecture
def create_network():
    net = nn.Sequential(
        nn.Linear(11, 511),
        nn.ReLU(),
        nn.BatchNorm1d(511),
        nn.Dropout(0.201),

        nn.Linear(511, 141),
        nn.ReLU(),
        nn.BatchNorm1d(141),
        nn.Dropout(0.496),

        nn.Linear(141, 127),
        nn.ReLU(),
        nn.BatchNorm1d(127),
        nn.Dropout(0.106),

        nn.Linear(127, 16),
        nn.ReLU(),
        nn.BatchNorm1d(16),
        nn.Dropout(0.28),

        nn.Linear(16, 1)
    )
    return net


# Load necessary components
@st.cache_resource
def load_components():
    seed_everything(42)

    # Initialize model
    net = create_network()
    model = CoxPH(net, tt.optim.Adam(lr=0.0045, weight_decay=0.00097))

    # Load model weights
    model.load_model_weights("survival_model.pth", map_location='cpu')

    # Load scaler and baseline hazard
    scaler = joblib.load("scaler1.pkl")
    baseline_hazard = pd.read_csv("baseline_hazard.csv", index_col=0)

    return model, scaler, baseline_hazard


model, scaler, baseline_hazard = load_components()

LIMITS = {
    "weight.g.": (400, 2000),
    "Apgar5": (0, 10),
    "GDW": (20, 42),
    "HR": (60, 200),
    "Saturation": (40, 100)
}

FEATURES = [
    "BOH", "weight.g.", "Apgar5", "GDW", "RF", "HR", "Saturation", "IVH", "DIC", "NE", "RDS"
]

LABELS = {
    "en": {
        "BOH": "Bad obestric history",
        "weight.g.": "Weight (g)",
        "Apgar5": "Apgar Score (5 min)",
        "GDW": "Gestational Age (weeks)",
        "RF": "Respiratory Failure",
        "HR": "Heart Rate (bpm)",
        "Saturation": "Oxygen Saturation (%)",
        "IVH": "Intraventricular Hemorrhage",
        "DIC": "DIC Syndrome",
        "NE": "Necrotizing Enterocolitis",
        "RDS": "Respiratory Distress Syndrome"
    },
    "ru": {
        "BOH": "Отягощенный акушерский анамнез",
        "weight.g.": "Вес (гр)",
        "Apgar5": "Оценка по Апгар (5-я мин)",
        "GDW": "Гестационный возраст (нед)",
        "RF": "Дыхательная недостаточность",
        "HR": "ЧСС (уд./мин.)",
        "Saturation": "Сатурация (%)",
        "IVH": "Внутрижелудочковое кровоизлияние",
        "DIC": "ДВС-синдром",
        "NE": "Некротизирующий энтероколит",
        "RDS": "Синдром дыхательных расстройств"
    }
}


def preprocess_input(input_dict):
    # Ensure the features are in the correct order
    arr = np.array([input_dict[feat] for feat in FEATURES]).reshape(1, -1)
    arr_scaled = scaler.transform(arr)
    return torch.tensor(arr_scaled, dtype=torch.float32)


# Streamlit UI starts here
current_lang = st.sidebar.selectbox("Select language", ["English", "Русский"])
lang_code = "en" if current_lang == "English" else "ru"
labels = LABELS[lang_code]

st.title("🩺 " + (
    "Preterm Infant Survival Calculator" if lang_code == "en" else "Калькулятор функции выживаемости недоношенных детей"))
st.info(
    "Enter patient data below to calculate individual risk and survival function."
    if lang_code == "en" else
    "Введите данные пациента ниже для расчета индивидуального риска и прогнозируемой функции выживаемости."
)

st.sidebar.header("Instructions" if lang_code == "en" else "Инструкции")
st.sidebar.markdown(
 "This DeepSurv-based calculator estimates individual survival probability for very low birth weight (VLBW) preterm infants. "
    "It supports both initial risk assessment at NICU admission and dynamic prognosis updates as clinical conditions evolve.\n\n"
    
    "**Evaluation modes:**\n"
    "1. **Initial assessment (NICU admission):** Enter only baseline data reflecting the infant’s condition at birth and stabilization:\n"
    "   - Gestational age and birth weight\n"
    "   - Apgar score (5th minute)\n"
    "   - Heart rate and SpO₂ on admission\n"
    "   - Maternal obstetric history\n"
    "   *Note: Complications (RDS, IVH, NEC, DIC) should be marked as 'No' unless already confirmed.*\n\n"
    
    "2. **Dynamic assessment (during treatment):** Update inputs when clinical status changes:\n"
    "   - Include complications (RDS, IVH, NEC, DIC)\n"
    "   - The model recalculates survival trajectory based on newly developed conditions\n\n"
    
    "**Input rules:**\n"
    "- **Numeric features:** Use sliders to select exact values\n"
    "- **Binary features (Yes/No):** Indicate presence or absence of conditions\n"
    "- **Respiratory failure (RF):** Select severity grade (2 or 3)\n\n"
    
    "**Interpretation and safe use:**\n"
    "1. The model is dynamic and should be updated as the patient’s condition evolves for real-time monitoring\n"
    "2. Results represent probabilistic estimates, not guaranteed outcomes\n"
    "3. Use as a clinical decision support tool alongside standard assessment methods\n"
    "4. Key evaluation timepoints: 7 and 28 days\n\n"
    
    "- Click **'Calculate Survival Function'** to generate results"
        if lang_code == "en" else
  "Калькулятор на основе DeepSurv оценивает индивидуальную вероятность выживаемости недоношенных детей с очень низкой массой тела (VLBW). "
        "Поддерживает первичную оценку при поступлении в ОРИТН и динамическое обновление прогноза.\n\n"
        
        "**Режимы оценки:**\n"
        "1. **Первичная оценка (при поступлении в ОРИТН):** Вводятся только исходные данные:\n"
        "   - Гестационный возраст и масса тела при рождении\n"
        "   - Апгар (5-я минута)\n"
        "   - ЧСС и SpO₂ при поступлении\n"
        "   - Акушерский анамнез матери\n"
        "   *Примечание: Осложнения (РДС, ВЖК, НЭК, ДВС) отмечаются как «Нет», если не подтверждены.*\n\n"
        
        "2. **Динамическая оценка (в процессе лечения):** Обновляйте данные при изменении состояния:\n"
        "   - Добавляются осложнения (РДС, ВЖК, НЭК, ДВС)\n"
        "   - Модель пересчитывает прогноз\n\n"
        
        "**Правила заполнения:**\n"
        "- **Числовые параметры:** Используйте ползунки\n"
        "- **Бинарные признаки (Да/Нет):** Укажите наличие или отсутствие\n"
        "- **Дыхательная недостаточность (ДН):** Степень 2 или 3\n\n"
        
        "**Интерпретация и использование:**\n"
        "1. Модель динамическая — обновляйте данные при изменении состояния\n"
        "2. Результат — вероятность, а не гарантированный исход\n"
        "3. Использовать вместе с клинической оценкой\n"
        "4. Контрольные точки: 7 и 28 сутки\n\n"
        
        "- Нажмите **'Рассчитать функцию выживаемости'**"
    )
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.markdown("**Enter Patient Data**" if lang_code == "en" else "**Введите данные пациента**")
    user_input = {}

    for feat in FEATURES:
        if feat == "RF":
            user_input[feat] = st.radio(labels[feat], [2, 3], horizontal=True)
        elif feat in ["BOH", "IVH", "DIC", "NE", "RDS"]:  # Binary features
            user_input[feat] = st.radio(labels[feat], [0, 1], format_func=lambda x: "No" if x == 0 else "Yes",
                                        horizontal=True)
        else:
            min_val, max_val = LIMITS.get(feat, (0, 9999))
            user_input[feat] = st.slider(labels[feat], float(min_val), float(max_val), float(min_val), step=1.0)

    calc_button = st.button(
        "📊 Calculate Survival Function" if lang_code == "en" else "📊 Рассчитать функцию выживаемости")

with col2:
    if calc_button:
        try:
            x_patient = preprocess_input(user_input)
            risk_score = model.predict(x_patient).item()
            st.write(f"**Individual Risk (log hazard):** {risk_score:.3f}")

            times = baseline_hazard.index.astype(float)
            H0_t = baseline_hazard.values.astype(float)
            S_t = np.exp(-H0_t * np.exp(risk_score))

            fig, ax = plt.subplots(figsize=(7, 4))
            ax.plot(times, S_t, color="blue", lw=2, label="Survival Function")
            ax.set_xlabel("Time (days)" if lang_code == "en" else "Время (дни)")
            ax.set_ylabel("Survival Probability" if lang_code == "en" else "Вероятность выживания")
            ax.legend()
            ax.grid(True)
            st.pyplot(fig)


            def get_survival_probability(time_point):
                idx = np.argmin(np.abs(times - time_point))
                return float(S_t[idx]) * 100  # in percent


            surv_7 = get_survival_probability(7)
            surv_28 = get_survival_probability(28)
            surv_100 = get_survival_probability(100)

            st.markdown(f"""
            **Survival Probability:**
            - 7 Days: **{surv_7:.2f}%**
            - 28 Days: **{surv_28:.2f}%**
            - 100 Days: **{surv_100:.2f}%**
            """ if lang_code == "en" else f"""
            **Вероятность выживания:**
            - 7 дней: **{surv_7:.2f}%**
            - 28 дней: **{surv_28:.2f}%**
            - 100 дней: **{surv_100:.2f}%**
            """)

            st.markdown(
                """
                **Graph Interpretation:**  
                - The curve shows the probability of patient survival over time.  
                - The higher the curve, the greater the survival probability at that interval.  
                - A higher risk (greater log hazard) results in a steeper decline.
                """ if lang_code == "en" else """
                **Интерпретация графика:**  
                - Кривая показывает вероятность выживания пациента с течением времени.  
                - Чем выше кривая, тем выше вероятность выживания на данном интервале.  
                - При высоком риске (большем log hazard) кривая будет падать быстрее.
                """)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.info("Enter the data and click 'Calculate survival function'"
                if lang_code == "en" else
                "Введите данные и нажмите 'Рассчитать функцию выживаемости'")

st.markdown("<hr/>", unsafe_allow_html=True)