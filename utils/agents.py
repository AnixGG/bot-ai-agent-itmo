import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import os
from utils.parser import parser_response, decrease

id_key = os.environ.get("id_key")
api_key = os.environ.get("api_key")
api_search_key = os.environ.get("api_key")


class SearchContextAgent:
    def __init__(self):
        self.url = f"https://yandex.ru/search/xml?folderid={id_key}&apikey={api_search_key}&query="

    async def search(self, question):
        self.url += question + "site:[itmo.ru]"
        response = requests.get(self.url)
        if response.status_code != 200:
            return "Для этого вопроса нет контекста", ["Ссылки не использовались"]

        root = ET.fromstring(response.text)

        context = []
        urls = []
        count = 3

        for doc in root.findall('.//doc'):
            url = doc.find('url').text
            urls.append(url)

            curr_response = requests.get(url)
            if curr_response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            context.extend([f"<source>{url}</source>", text])
            del soup
            count -= 1
            if count == 0:
                break

        s = '\n'.join(context)
        return decrease(s), urls


class AiAgent:
    def __init__(self):
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {api_key}",
            "x-folder-id": id_key,
        }
        self.prompt = {
            "modelUri": f"gpt://{id_key}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "max_tokens": 6000,
            },
            "messages": [
                {
                    "role": "system",
                    "text": "",
                },
                {
                    "role": "user",
                    "text": "",
                },
            ]
        }


class AiGenerateAnswAgent(AiAgent):
    def __init__(self):
        super().__init__()
        self.prompt["messages"][0]["text"] = f"""
                                            Тебе зададут вопрос, используй предложенный контекст и дай четкий ответ.
                                            Текст должен быть четким и понятным.
                                            """

    def _create_prompt(self, question, context):
        req = f"""
            Вопрос: {question}
            Итоговый ответ должен выглядеть так: 
            text, string
            
            Контекст: 
            {context}
            """
        self.prompt["messages"][1]["text"] = decrease(req)

    def search_answer(self, question, context):
        self._create_prompt(question, context)
        result = requests.post(self.url, headers=self.headers, json=self.prompt).json()
        result = parser_response(result)

        return result


class AiGenerateChooseAgent(AiAgent):
    def __init__(self):
        super().__init__()
        self.prompt["messages"][0]["text"] = f"""
                                        Тебе зададут вопрос с вариантами ответов, используй предложенный контекст и дай четкий ответ. Дополнительно 
                                        выведи краткое и четкое пояснение своего выбора. 
                                        Текст объяснения должен быть логичным и хорошо объяснять причину выбора.
                                        """

    async def generate(self, question, variants, context):

        self._create_prompt(question, variants, context)
        result = requests.post(self.url, headers=self.headers, json=self.prompt).json()
        result = parser_response(result)

        return result

    def _create_prompt(self, question, variants, context):
        joined_variants = '\n'.join(variants)
        req = f"""
                Вопрос: {question}
                Варианты ответов, среди которых гарантировано есть правильный ответ: 
                {joined_variants}
                Выведи ответ строго следующим образом:
                answer: только номер варианта ответа, int,
                reasoning: пояснение своего выбора, string, пример <a> text
                Итоговый ответ должен выглядеть так: 
                answer: 5,
                reasoning: text
                Контекст: 
                {context}
                """

        self.prompt["messages"][1]["text"] = decrease(req)


class AiNewsAgent(AiAgent):
    def __init__(self):
        super().__init__()
        self.news_url = "https://news.itmo.ru/ru/"
        self.prompt["messages"][0]["text"] = f"""
                                                Тебе дадут описание новостей и ссылки на соответствующие статьи.
                                                Ссылки будут в таком виде <guid> link.ru </guid> после каждого описания. 
                                                Поясняю: 1 описание новости <guid> link_1.ru </guid> 2 описание новости </guid> link_2.ru </guid> ... 
                                                """

    async def parse_new(self):
        descriptions = []
        hrefs = []
        response = requests.get(self.news_url)
        soup = BeautifulSoup(response.text, "html.parser")
        top_news = soup.select_one(".accent .side p")
        top_href = soup.select_one(".accent .side a")

        if top_news:
            descriptions.append(top_news.text.strip())
        if top_href:
            hrefs.append(top_href["href"])

        for news in soup.select(".triplet li")[:2]:
            title = news.select_one("h4 a")
            if title:
                descriptions.append(title.text.strip())
                hrefs.append(title["href"])

        req = f"""
                Тебе дается описания последних новостей университета Итмо.
                Кратко и четко опиши их, сохраняя смысл. Описания отделены друг от друга специальным символом <>
                Описания: 
                {' <> '.join(descriptions)}
                """

        self.prompt["messages"][1]["text"] = decrease(req)

        result = requests.post(self.url, headers=self.headers, json=self.prompt).json()
        result = parser_response(result)
        return result, hrefs


class AiClassifierNewsAgent(AiAgent):
    def __init__(self):
        super().__init__()
        self.prompt["messages"][0]["text"] = """
                                            Насколько схож по смыслу с фразой 'Показать последние новости ITMO' следующие текста.
                                            Выведи только 1 число: 1 если похожи, 0 если нет.
                                                """

    def _create_prompt(self, question):
        self.prompt["messages"][1]["text"] = question

    async def classify(self, question) -> bool:  # is news request or not
        self._create_prompt(question)

        result = requests.post(self.url, headers=self.headers, json=self.prompt).json()
        result = parser_response(result)
        try:
            result = int(result)
        except Exception:
            result = 1

        return result == 1
