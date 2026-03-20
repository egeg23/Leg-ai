"""
Модуль интеграции с API Кими (Moonshot AI) для юридического сервиса.
Версия с MOCK-ответами (без реальных API запросов).

Предоставляет функции для:
- Анализа документов дела
- Генерации юридических документов
- Проверки согласованности контекста
"""

import json
import random
import time
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Типы юридических документов."""
    COMPLAINT = "complaint"      # Исковое заявление
    APPEAL = "appeal"            # Апелляционная жалоба
    PETITION = "petition"        # Претензия
    STATEMENT = "statement"      # Стратегия защиты


class KimiAPIError(Exception):
    """Базовое исключение для ошибок API Кими."""
    pass


class RateLimitError(KimiAPIError):
    """Исключение при превышении лимита запросов."""
    pass


# =============================================================================
# MOCK ДАННЫЕ ДЛЯ ГЕНЕРАЦИИ
# =============================================================================

MOCK_LEGAL_ANALYSIS = {
    "document_list": [
        "Договор займа от 15.01.2024 между сторонами",
        "Расписка в получении денежных средств",
        "Письменное требование об уплате долга"
    ],
    "legal_summary": """На основании представленных документов установлено наличие 
денежного обязательства ответчика перед истцом. Договор займа заключен в простой 
письменной форме, что соответствует требованиям ст. 808 ГК РФ. Ответчик не исполнил 
обязательство по возврату суммы займа в срок, установленный договором.""",
    "collisions": [
        "Необходимо уточнить размер процентов за просрочку согласно ст. 395 ГК РФ"
    ],
    "contradictions": [],
    "recommendations": [
        "Подготовить исковое заявление в суд",
        "Рассчитать проценты за просрочку по состоянию на дату подачи иска",
        "Убедиться в правильности адреса ответчика для направления копии искового заявления"
    ]
}

MOCK_DOCUMENT_TEMPLATES = {
    DocumentType.COMPLAINT: """
В {court_name}

Истец: {plaintiff_name}
Адрес: {plaintiff_address}

Ответчик: {defendant_name}
Адрес: {defendant_address}

Цена иска: {claim_amount} рублей

ИСКОВОЕ ЗАЯВЛЕНИЕ
о взыскании задолженности по договору займа


1. ОПИСАНИЕ ФАКТИЧЕСКИХ ОБСТОЯТЕЛЬСТВ

{date} года между Истцом и Ответчиком был заключен договор займа (далее — «Договор»), 
согласно которому Ответчик получил от Истца в долг денежные средства в размере {loan_amount} рублей.

Согласно условиям Договора, Ответчик обязался возвратить сумму займа не поздее {due_date}.

Денежные средства были фактически переданы Ответчику, о чем свидетельствует расписка 
в получении денежных средств от {date}.

Однако, в установленный срок Ответчик не исполнил свое обязательство по возврату 
задолженности. Несмотря на неоднократные устные и письменные требования, Ответчик 
отказывается возвращать долг.

2. ПРАВОВОЕ ОБОСНОВАНИЕ ПОЗИЦИИ ИСТЦА

В соответствии со статьей 807 Гражданского кодекса Российской Федерации (далее — ГК РФ) 
по договору займа одна сторона (займодавец) передает в собственность другой стороне 
(заемщику) деньги или другие вещи, определяемые родовыми признаками, а заемщик 
обязуется возвратить займодавцу такую же сумму денег (сумму займа) или равное 
количество других полученных им вещей того же рода и качества.

Согласно статье 309 ГК РФ обязательства должны исполняться надлежащим образом 
в соответствии с условиями обязательства и требованиями закона.

В силу статьи 310 ГК РФ односторонний отказ от исполнения обязательства и 
одностороннее изменение его условий не допускаются.

Статья 811 ГК РФ предусматривает обязанность заемщика возвратить сумму займа 
в срок, установленный договором.

3. ДОКАЗАТЕЛЬСТВА

В подтверждение заявленных требований истец представляет следующие документы:

1. Договор займа от {date} года;
2. Расписку Ответчика в получении денежных средств;
3. Выписку со счета об осуществлении перевода денежных средств;
4. Письменное требование об уплате долга от {demand_date};
5. Документы, подтверждающие судебные расходы.

4. РАСЧЕТ СУДЕБНЫХ РАСХОДОВ

Государственная пошлина: {court_fee} руб.
Расходы на представителя: {lawyer_fee} руб.

5. ПРОСИТЕЛЬНАЯ ЧАСТЬ

На основании изложенного, руководствуясь статьями 807, 808, 809, 810, 811 ГК РФ, 
статьями 131, 132 Гражданского процессуального кодекса РФ,

ПРОШУ:

1. Взыскать с Ответчика в пользу Истца сумму основного долга в размере {loan_amount} рублей.
2. Взыскать с Ответчика проценты за пользование займом в размере {interest_amount} рублей.
3. Взыскать с Ответчика проценты за просрочку возврата займа в размере {penalty_amount} рублей.
4. Взыскать с Ответчика судебные расходы в размере {total_expenses} рублей.
5. Взыскать с Ответчика компенсацию морального вреда в размере {moral_damage} рублей (при наличии оснований).

ПРИЛОЖЕНИЕ:

1. Копия искового заявления для Ответчика;
2. Договор займа от {date} года;
3. Расписка в получении денежных средств;
4. Выписка с банковского счета;
5. Письменное требование об уплате долга;
6. Документы, подтверждающие судебные расходы;
7. Документы, подтверждающие направление претензии;
8. Квитанция об оплате государственной пошлины.


{date_today} г.                                      _____________ / {plaintiff_name_short} /
                                                           (подпись)
""",

    DocumentType.APPEAL: """
В {court_name}

Апеллянт: {plaintiff_name}
Адрес: {plaintiff_address}

Лицо, участвующее в деле: {defendant_name}
Адрес: {defendant_address}

АПЕЛЛЯЦИОННАЯ ЖАЛОБА
на решение {lower_court_name} от {decision_date} по делу № {case_number}


Апеллянт считает решение {lower_court_name} от {decision_date} незаконным, 
необоснованным и подлежащим отмене по следующим основаниям:

1. НЕПРАВИЛЬНОЕ ПРИМЕНЕНИЕ НОРМ МАТЕРИАЛЬНОГО ПРАВА

Суд первой инстанции неверно применил положения ст. {article_violated} ГК РФ, 
что привело к неправильному разрешению спора.

При вынесении решения суд не учел следующие обстоятельства:
{relevant_facts}

В соответствии с разъяснениями, содержащимися в п. {paragraph_number} 
Постановления Пленума Верховного Суда РФ от {plenum_date} № {plenum_number} 
"{plenum_name}", 

{legal_position}

Таким образом, выводы суда первой инстанции противоречат установленным обстоятельствам 
дела и имеющимся в деле доказательствам.

2. НАРУШЕНИЕ НОРМ ПРОЦЕССУАЛЬНОГО ПРАВА

Судом первой инстанции допущены следующие нарушения процессуальных норм:

- Неполное исследование доказательств по делу (ст. 62 ГПК РФ);
- Неправильная оценка доказательств (ст. 67 ГПК РФ);
- Ограничение в праве на представление доказательств (ст. 35 ГПК РФ);
- Нарушение принципа состязательности (ст. 9 ГПК РФ).

Судом не были истребованы и не исследованы следующие доказательства:
{missing_evidence}

3. ОБСТОЯТЕЛЬСТВА, НЕ ИССЛЕДОВАННЫЕ СУДОМ

В ходе апелляционного рассмотрения должны быть исследованы следующие обстоятельства:
{additional_facts}

4. ПРОСИТЕЛЬНАЯ ЧАСТЬ

На основании изложенного, руководствуясь статьями 320, 321, 322, 323, 324 Гражданского 
процессуального кодекса Российской Федерации,

ПРОШУ:

1. Решение {lower_court_name} от {decision_date} по делу № {case_number} отменить 
   и принять по делу новое решение.
2. При отмене решения суда — {requested_ruling}.

ПРИЛОЖЕНИЕ:

1. Копия апелляционной жалобы для лица, участвующего в деле;
2. Дополнительные доказательства: {new_evidence_list};
3. Документы, подтверждающие уплату государственной пошлины;
4. Доверенность представителя (при наличии).


{date_today} г.                                      _____________ / {plaintiff_name_short} /
                                                           (подпись)
""",

    DocumentType.PETITION: """

                                                        {recipient}

Отправитель: {sender_name}
Адрес: {sender_address}
Телефон: {sender_phone}
E-mail: {sender_email}

ПРЕТЕНЗИЯ
о нарушении условий договора и требовании уплаты задолженности


Настоящим сообщаем, что между {party_a} и {party_b} был заключен 
{contract_type} № {contract_number} от {contract_date} (далее — "Договор").

В соответствии с условиями Договора, {obligation_description}.

Однако, по состоянию на {current_date}, {debtor_name} имеет задолженность 
перед {creditor_name} в размере:

- Основной долг: {principal_debt} рублей;
- Неустойка (пени): {penalty_amount} рублей;
- Проценты: {interest_amount} рублей;
- ИТОГО ЗАДОЛЖЕННОСТЬ: {total_debt} рублей.

{breach_description}

В соответствии со статьей 309 Гражданского кодекса Российской Федерации 
обязательства должны исполняться надлежащим образом в соответствии с условиями 
обязательства и требованиями закона, иного правового акта.

Статья 310 Гражданского кодекса РФ устанавливает, что односторонний отказ от 
исполнения обязательства и одностороннее изменение его условий не допускаются.

Согласно статье 330 Гражданского кодекса РФ неустойкой (штрафом, пеней) признается 
определенная законом или договором денежная сумма, которую должник обязан уплатить 
кредитору в случае неисполнения или ненадлежащего исполнения обязательства.

На основании изложенного и руководствуясь статьями 309, 310, 330, 395 ГК РФ,

ТРЕБУЕМ:

1. Уплатить задолженность в размере {total_debt} (__________________________) рублей 
   в течение 10 (десяти) рабочих дней с момента получения настоящей претензии.
2. В случае неуплаты задолженности в указанный срок будет вынужден обратиться 
   в суд с исковым заявлением о взыскании задолженности, неустойки, процентов 
   и возмещении судебных расходов.

Реквизиты для оплаты:
{payment_details}

Настоящая претензия составлена в двух экземплярах, один из которых направлен 
заказным письмом с уведомлением о вручении и описью вложения.


Приложения:
1. Копия Договора № {contract_number} от {contract_date};
2. Выписка из учетных документов о возникновении задолженности;
3. Расчет задолженности;
4. Квитанция об оплате услуг почты (при направлении).


{date_today} г.                                      _____________ / {sender_name_short} /
                                                           (подпись)


ИСПОЛНИТЕЛЮ:
_____________________________________________________________________________
(дата получения, подпись должностного лица, получившего претензию)
""",

    DocumentType.STATEMENT: """

СТРАТЕГИЯ ЗАЩИТЫ В СУДЕ

Дело №: {case_number}
Суд: {court_name}
Истец: {plaintiff_name}
Ответчик: {defendant_name}
Предмет спора: {dispute_subject}


1. ОБЩАЯ ХАРАКТЕРИСТИКА ДЕЛА

1.1. Суть спора:
{dispute_summary}

1.2. Позиция противоположной стороны:
{opponent_position}

1.3. Правовые риски:
{legal_risks}


2. СТРАТЕГИЧЕСКИЕ ЦЕЛИ

Основная цель: {main_goal}

Запасная цель (план "Б"): {backup_goal}


3. ПРАВОВОЕ ОБОСНОВАНИЕ ПОЗИЦИИ

3.1. Применимые нормы права:
{applicable_laws}

3.2. Судебная практика:
{case_law}

3.3. Доказательственная база:
{evidence_base}


4. ТАКТИКА ЗАЩИТЫ

4.1. На досудебной стадии:
{pre_trial_tactics}

4.2. На стадии подготовки дела к судебному разбирательству:
{preparation_tactics}

4.3. В судебном заседании:
{trial_tactics}

4.4. В апелляционной инстанции (при необходимости):
{appeal_tactics}


5. ВОЗМОЖНЫЕ ХОДАТАЙСТВА И ЗАПРОСЫ

5.1. Ходатайства о приобщении доказательств:
{evidence_requests}

5.2. Ходатайства об истребовании доказательств:
{evidence_motion}

5.3. Иные ходатайства:
{other_motions}


6. РАБОТА С ДОКАЗАТЕЛЬСТВАМИ

6.1. Доказательства, подтверждающие нашу позицию:
{favorable_evidence}

6.2. Доказательства, требующие опровержения:
{unfavorable_evidence}

6.3. Необходимые экспертизы:
{required_expertises}


7. КАЛЕНДАРНЫЙ ПЛАН

7.1. Дата подачи отзыва на исковое заявление: {response_deadline}
7.2. Дата подготовительного заседания: {preliminary_hearing}
7.3. Дата предполагаемого судебного разбирательства: {trial_date}
7.4. Срок обжалования решения: {appeal_deadline}


8. РИСКИ И ПЛАНИРОВАНИЕ

8.1. Возможные риски:
{risk_list}

8.2. План минимизации рисков:
{risk_mitigation}

8.3. Сценарий урегулирования спора мирным путем:
{settlement_scenario}


9. СТОИМОСТЬ ЗАЩИТЫ

9.1. Судебные расходы:
- Государственная пошлина: {court_fee} руб.
- Расходы на экспертизу: {expert_fee} руб.
- Иные расходы: {other_fees} руб.

9.2. Расходы на представителя: {lawyer_fees} руб.

9.3. ИТОГО: {total_costs} руб.


10. ЗАКЛЮЧЕНИЕ

{conclusion}


Составлено: {date_today}
Ответственный исполнитель: {lawyer_name}
"""
}


# =============================================================================
# MOCK ФУНКЦИИ API
# =============================================================================

def analyze_case_documents(documents_text: List[str], api_key: str = None) -> Dict[str, Any]:
    """
    MOCK: Анализирует документы по делу и возвращает структурированный отчет.
    
    Args:
        documents_text: Список текстов документов для анализа
        api_key: API ключ (игнорируется в mock-режиме)
        
    Returns:
        Словарь с результатами анализа
    """
    if not documents_text:
        raise ValueError("Список документов не может быть пустым")
    
    logger.info(f"[MOCK] Анализ {len(documents_text)} документов")
    
    # Имитация задержки обработки
    time.sleep(0.5)
    
    # Генерируем вариативный ответ на основе количества документов
    analysis = MOCK_LEGAL_ANALYSIS.copy()
    analysis["document_list"] = [
        f"Документ {i+1}: {doc[:50]}..." if len(doc) > 50 else f"Документ {i+1}: {doc}"
        for i, doc in enumerate(documents_text)
    ]
    
    # Добавляем случайные противоречия если документов больше 1
    if len(documents_text) > 1:
        analysis["contradictions"] = [
            "Даты в документах требуют дополнительной проверки",
            "Рекомендуется уточнить полные реквизиты сторон"
        ]
    
    return analysis


def generate_legal_document(
    case_data: Dict[str, Any], 
    document_type: str, 
    api_key: str = None
) -> str:
    """
    MOCK: Генерирует юридический документ.
    
    Args:
        case_data: Данные дела для генерации документа
        document_type: Тип документа ('complaint', 'appeal', 'petition', 'statement')
        api_key: API ключ (игнорируется в mock-режиме)
        
    Returns:
        Текст сгенерированного юридического документа
    """
    if not case_data:
        raise ValueError("Данные дела не могут быть пустыми")
    
    # Преобразуем строковый тип в enum
    try:
        doc_type = DocumentType(document_type.lower())
    except ValueError:
        valid_types = [t.value for t in DocumentType]
        raise ValueError(f"Недопустимый тип документа. Допустимые значения: {valid_types}")
    
    logger.info(f"[MOCK] Генерация документа типа: {doc_type.value}")
    
    # Имитация задержки генерации
    time.sleep(0.5)
    
    # Получаем шаблон
    template = MOCK_DOCUMENT_TEMPLATES.get(doc_type, MOCK_DOCUMENT_TEMPLATES[DocumentType.COMPLAINT])
    
    # Подготовка данных для подстановки
    defaults = {
        # Общие поля
        'court_name': case_data.get('court_name', '[НАИМЕНОВАНИЕ СУДА]'),
        'plaintiff_name': case_data.get('plaintiff', {}).get('name', '[ФИО ИСТЦА]'),
        'plaintiff_name_short': case_data.get('plaintiff', {}).get('name', '[ФИО]').split()[0] if case_data.get('plaintiff') else '[ФИО]',
        'plaintiff_address': case_data.get('plaintiff', {}).get('address', '[АДРЕС ИСТЦА]'),
        'defendant_name': case_data.get('defendant', {}).get('name', '[ФИО ОТВЕТЧИКА]'),
        'defendant_address': case_data.get('defendant', {}).get('address', '[АДРЕС ОТВЕТЧИКА]'),
        'claim_amount': case_data.get('claim_amount', '[СУММА ИСКА]'),
        'date_today': case_data.get('date', '«___» _________ 2025'),
        
        # Поля для искового заявления
        'date': case_data.get('date', '[ДАТА ДОГОВОРА]'),
        'loan_amount': case_data.get('loan_amount', '[СУММА ЗАЙМА]'),
        'due_date': case_data.get('due_date', '[СРОК ВОЗВРАТА]'),
        'demand_date': case_data.get('demand_date', '[ДАТА ТРЕБОВАНИЯ]'),
        'interest_amount': case_data.get('interest_amount', '[СУММА ПРОЦЕНТОВ]'),
        'penalty_amount': case_data.get('penalty_amount', '[НЕУСТОЙКА]'),
        'court_fee': case_data.get('court_fee', '[ГОСПОШЛИНА]'),
        'lawyer_fee': case_data.get('lawyer_fee', '[РАСХОДЫ НА ПРЕДСТАВИТЕЛЯ]'),
        'total_expenses': case_data.get('total_expenses', '[ВСЕГО РАСХОДОВ]'),
        'moral_damage': case_data.get('moral_damage', '[МОРАЛЬНЫЙ ВРЕД]'),
        
        # Поля для апелляции
        'lower_court_name': case_data.get('lower_court_name', '[НАЗВАНИЕ СУДА ПЕРВОЙ ИНСТАНЦИИ]'),
        'decision_date': case_data.get('decision_date', '[ДАТА РЕШЕНИЯ]'),
        'case_number': case_data.get('case_number', '[НОМЕР ДЕЛА]'),
        'article_violated': case_data.get('article_violated', '[НОМЕР СТАТЬИ]'),
        'relevant_facts': case_data.get('relevant_facts', '[УКАЖИТЕ РЕЛЕВАНТНЫЕ ФАКТЫ]'),
        'paragraph_number': case_data.get('paragraph_number', '[ПУНКТ]'),
        'plenum_date': case_data.get('plenum_date', '[ДАТА ПЛЕНУМА]'),
        'plenum_number': case_data.get('plenum_number', '[НОМЕР ПЛЕНУМА]'),
        'plenum_name': case_data.get('plenum_name', '[НАЗВАНИЕ ПЛЕНУМА]'),
        'legal_position': case_data.get('legal_position', '[ПРАВОВАЯ ПОЗИЦИЯ]'),
        'missing_evidence': case_data.get('missing_evidence', '[ОТСУТСТВУЮЩИЕ ДОКАЗАТЕЛЬСТВА]'),
        'additional_facts': case_data.get('additional_facts', '[ДОПОЛНИТЕЛЬНЫЕ ФАКТЫ]'),
        'requested_ruling': case_data.get('requested_ruling', '[ТРЕБУЕМОЕ РЕШЕНИЕ]'),
        'new_evidence_list': case_data.get('new_evidence_list', '[НОВЫЕ ДОКАЗАТЕЛЬСТВА]'),
        
        # Поля для претензии
        'recipient': case_data.get('recipient', '[АДРЕСАТ]'),
        'sender_name': case_data.get('sender_name', case_data.get('plaintiff', {}).get('name', '[ОТПРАВИТЕЛЬ]')),
        'sender_name_short': case_data.get('sender_name', case_data.get('plaintiff', {}).get('name', '[ФИО]')).split()[0] if case_data.get('sender_name') or case_data.get('plaintiff') else '[ФИО]',
        'sender_address': case_data.get('sender_address', case_data.get('plaintiff', {}).get('address', '[АДРЕС ОТПРАВИТЕЛЯ]')),
        'sender_phone': case_data.get('sender_phone', '[ТЕЛЕФОН]'),
        'sender_email': case_data.get('sender_email', '[EMAIL]'),
        'party_a': case_data.get('party_a', '[СТОРОНА А]'),
        'party_b': case_data.get('party_b', '[СТОРОНА Б]'),
        'contract_type': case_data.get('contract_type', '[ТИП ДОГОВОРА]'),
        'contract_number': case_data.get('contract_number', '[НОМЕР ДОГОВОРА]'),
        'contract_date': case_data.get('contract_date', '[ДАТА ДОГОВОРА]'),
        'obligation_description': case_data.get('obligation_description', '[ОПИСАНИЕ ОБЯЗАТЕЛЬСТВА]'),
        'current_date': case_data.get('current_date', '[ТЕКУЩАЯ ДАТА]'),
        'debtor_name': case_data.get('debtor_name', '[ДОЛЖНИК]'),
        'creditor_name': case_data.get('creditor_name', '[КРЕДИТОР]'),
        'principal_debt': case_data.get('principal_debt', '[ОСНОВНОЙ ДОЛГ]'),
        'total_debt': case_data.get('total_debt', '[ОБЩАЯ СУММА]'),
        'breach_description': case_data.get('breach_description', '[ОПИСАНИЕ НАРУШЕНИЯ]'),
        'payment_details': case_data.get('payment_details', '[РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ]'),
        
        # Поля для стратегии защиты
        'dispute_subject': case_data.get('dispute_subject', '[ПРЕДМЕТ СПОРА]'),
        'dispute_summary': case_data.get('dispute_summary', '[ОПИСАНИЕ СПОРА]'),
        'opponent_position': case_data.get('opponent_position', '[ПОЗИЦИЯ ПРОТИВОПОЛОЖНОЙ СТОРОНЫ]'),
        'legal_risks': case_data.get('legal_risks', '[ПРАВОВЫЕ РИСКИ]'),
        'main_goal': case_data.get('main_goal', '[ОСНОВНАЯ ЦЕЛЬ]'),
        'backup_goal': case_data.get('backup_goal', '[ЗАПАСНАЯ ЦЕЛЬ]'),
        'applicable_laws': case_data.get('applicable_laws', '[ПРИМЕНИМЫЕ ЗАКОНЫ]'),
        'case_law': case_data.get('case_law', '[СУДЕБНАЯ ПРАКТИКА]'),
        'evidence_base': case_data.get('evidence_base', '[ДОКАЗАТЕЛЬСТВЕННАЯ БАЗА]'),
        'pre_trial_tactics': case_data.get('pre_trial_tactics', '[ТАКТИКА НА ДОСУДЕБНОЙ СТАДИИ]'),
        'preparation_tactics': case_data.get('preparation_tactics', '[ТАКТИКА ПОДГОТОВКИ]'),
        'trial_tactics': case_data.get('trial_tactics', '[ТАКТИКА В СУДЕБНОМ ЗАСЕДАНИИ]'),
        'appeal_tactics': case_data.get('appeal_tactics', '[ТАКТИКА АПЕЛЛЯЦИИ]'),
        'evidence_requests': case_data.get('evidence_requests', '[ХОДАТАЙСТВА О ДОКАЗАТЕЛЬСТВАХ]'),
        'evidence_motion': case_data.get('evidence_motion', '[ИСТРЕБОВАНИЕ ДОКАЗАТЕЛЬСТВ]'),
        'other_motions': case_data.get('other_motions', '[ИНЫЕ ХОДАТАЙСТВА]'),
        'favorable_evidence': case_data.get('favorable_evidence', '[ПОЛОЖИТЕЛЬНЫЕ ДОКАЗАТЕЛЬСТВА]'),
        'unfavorable_evidence': case_data.get('unfavorable_evidence', '[ОТРИЦАТЕЛЬНЫЕ ДОКАЗАТЕЛЬСТВА]'),
        'required_expertises': case_data.get('required_expertises', '[ТРЕБУЕМЫЕ ЭКСПЕРТИЗЫ]'),
        'response_deadline': case_data.get('response_deadline', '[СРОК ОТЗЫВА]'),
        'preliminary_hearing': case_data.get('preliminary_hearing', '[ДАТА ПОДГОТОВИТЕЛЬНОГО ЗАСЕДАНИЯ]'),
        'trial_date': case_data.get('trial_date', '[ДАТА СУДЕБНОГО РАЗБИРАТЕЛЬСТВА]'),
        'appeal_deadline': case_data.get('appeal_deadline', '[СРОК ОБЖАЛОВАНИЯ]'),
        'risk_list': case_data.get('risk_list', '[СПИСОК РИСКОВ]'),
        'risk_mitigation': case_data.get('risk_mitigation', '[МИНИМИЗАЦИЯ РИСКОВ]'),
        'settlement_scenario': case_data.get('settlement_scenario', '[МИРОВОЕ СОГЛАШЕНИЕ]'),
        'expert_fee': case_data.get('expert_fee', '[СТОИМОСТЬ ЭКСПЕРТИЗЫ]'),
        'other_fees': case_data.get('other_fees', '[ИНЫЕ РАСХОДЫ]'),
        'lawyer_fees': case_data.get('lawyer_fees', '[ГОНОРАР АДВОКАТА]'),
        'total_costs': case_data.get('total_costs', '[ОБЩАЯ СТОИМОСТЬ]'),
        'conclusion': case_data.get('conclusion', '[ЗАКЛЮЧЕНИЕ]'),
        'lawyer_name': case_data.get('lawyer_name', '[ФИО ЮРИСТА]'),
    }
    
    # Заполняем шаблон
    try:
        document = template.format(**defaults)
    except KeyError as e:
        logger.warning(f"Не заполнено поле: {e}")
        document = template
    
    return document.strip()


def check_context_consistency(documents: List[str], api_key: str = None) -> Dict[str, Any]:
    """
    MOCK: Проверяет согласованность контекста между документами.
    
    Args:
        documents: Список текстов документов для проверки
        api_key: API ключ (игнорируется в mock-режиме)
        
    Returns:
        Словарь с результатами проверки
    """
    if not documents or len(documents) < 2:
        raise ValueError("Для проверки согласованности требуется минимум 2 документа")
    
    logger.info(f"[MOCK] Проверка согласованности {len(documents)} документов")
    
    # Имитация задержки проверки
    time.sleep(0.3)
    
    # В mock-режиме считаем документы согласованными
    return {
        "consistent": True,
        "issues": []
    }


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def get_document_type_name(doc_type: str) -> str:
    """Возвращает русское название типа документа."""
    names = {
        'complaint': 'Исковое заявление',
        'appeal': 'Апелляционная жалоба',
        'petition': 'Претензия',
        'statement': 'Стратегия защиты в суде'
    }
    return names.get(doc_type.lower(), 'Документ')


def get_document_type_enum(doc_type: str) -> Optional[DocumentType]:
    """Преобразует строковый тип в enum."""
    try:
        return DocumentType(doc_type.lower())
    except ValueError:
        return None


# =============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MOCK РЕЖИМ KIMI API - ТЕСТИРОВАНИЕ")
    print("=" * 70)
    
    # Тест 1: Анализ документов
    print("\n>>> Тест 1: Анализ документов")
    print("-" * 50)
    
    test_docs = [
        "Договор займа от 15.01.2024 на сумму 100000 руб.",
        "Расписка в получении денежных средств",
        "Требование об уплате долга от 01.03.2024"
    ]
    
    try:
        result = analyze_case_documents(test_docs)
        print(f"✓ Анализ выполнен")
        print(f"  Документов: {len(result['document_list'])}")
        print(f"  Противоречий: {len(result['contradictions'])}")
        print(f"  Рекомендаций: {len(result['recommendations'])}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Тест 2: Генерация искового заявления
    print("\n>>> Тест 2: Генерация искового заявления")
    print("-" * 50)
    
    test_case_data = {
        'court_name': 'Мировой судья судебного участка № 123',
        'plaintiff': {
            'name': 'Иванов Иван Иванович',
            'address': 'г. Москва, ул. Ленина, д. 10'
        },
        'defendant': {
            'name': 'Петров Петр Петрович',
            'address': 'г. Москва, ул. Пушкина, д. 5'
        },
        'claim_amount': '103 500',
        'date': '15.01.2024',
        'loan_amount': '100 000',
        'due_date': '15.04.2024',
        'date_today': '"15" марта 2025 г.'
    }
    
    try:
        document = generate_legal_document(test_case_data, 'complaint')
        print(f"✓ Документ сгенерирован")
        print(f"  Первые 200 символов: {document[:200]}...")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Тест 3: Генерация претензии
    print("\n>>> Тест 3: Генерация претензии")
    print("-" * 50)
    
    try:
        document = generate_legal_document(test_case_data, 'petition')
        print(f"✓ Претензия сгенерирована")
        print(f"  Первые 200 символов: {document[:200]}...")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Тест 4: Проверка согласованности
    print("\n>>> Тест 4: Проверка согласованности")
    print("-" * 50)
    
    try:
        result = check_context_consistency(test_docs)
        print(f"✓ Проверка выполнена")
        print(f"  Согласованность: {'Да' if result['consistent'] else 'Нет'}")
        print(f"  Проблем: {len(result['issues'])}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 70)
