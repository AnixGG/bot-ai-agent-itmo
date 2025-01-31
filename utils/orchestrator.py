from utils.agents import *
from utils.parser import parser_question
import asyncio


class Orchestrator:
    def __init__(self):
        self.classifier_agent = AiClassifierNewsAgent()
        self.news_agent = AiNewsAgent()
        self.search_context_agent = SearchContextAgent()
        self.ai_variants_agent = AiGenerateChooseAgent()
        self.ai_answer_agent = AiGenerateAnswAgent()

    async def control(self, q):
        question, variants = parser_question(q)
        is_about_news = await self.classifier_agent.classify(question)
        if not len(variants) and is_about_news:
            results, urls = await self.news_agent.parse_new()
            if not len(urls):
                urls = [self.news_agent.news_url]
            data = {"answer": -1,
                    "source": urls,
                    "reasoning": results}
            return data

        context, urls = await self.search_context_agent.search(question)

        if not len(variants):
            results = self.ai_answer_agent.search_answer(question, context)
            data = {"answer": -1,
                    "source": urls[:3],
                    "reasoning": results}
            return data
        results = await self.ai_variants_agent.generate(question, variants, context)
        results_splitted = results.split('\n')
        id_answer = -1
        try:
            id_answer = int(results_splitted[0].split()[1][:-1])
        except:
            pass

        data = {"answer": id_answer,
                "source": urls[:3],
                "reasoning": ' '.join(results_splitted[1].split()[1:])}
        return data


async def main():
    o = Orchestrator()
    s = """В каком рейтинге (по состоянию на 2021 год) ИТМО впервые вошёл в
топ-400 мировых университетов?\n1. ARWU (Shanghai Ranking)\n2. Times Higher
Education (THE) World University Rankings\n3. QS World University Rankings\n4. U.S.
News & World Report Best Global Universities"""
    asyncio.ensure_future(o.control(s))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
