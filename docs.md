import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { ChatOpenAI } from "@langchain/openai";
import { createAgent } from "langchain";

const financeTickerLookup = tool(
  async ({ query }) => {
    const response = await fetch(
      `https://financialmodelingprep.com/stable/search-symbol?query=${encodeURIComponent(query)}&apikey=${process.env.FMP_API_KEY}`
    );
    const data = await response.json();
    return data.slice(0, 5).map((item: any) => ({
      symbol: item.symbol,
      name: item.name,
      exchange: item.exchange,
    }));
  },
  {
    name: "finance_tickers_lookup",
    description: "Ищет биржевые тикеры по названию компании или части тикера.",
    schema: z.object({ query: z.string().min(1) }),
  }
);

const financeQuotes = tool(
  async ({ tickerSymbols, fields }) => {
    const params = new URLSearchParams({
      symbols: tickerSymbols.join(","),
      apikey: process.env.FMP_API_KEY || "",
    });
    const response = await fetch(
      `https://financialmodelingprep.com/stable/quote?${params}`
    );
    const data = await response.json();
    return data.map((item: any) => {
      const row: Record<string, any> = { symbol: item.symbol };
      for (const field of fields) {
        if (item[field] !== undefined) row[field] = item[field];
      }
      return row;
    });
  },
  {
    name: "finance_quotes",
    description: "Возвращает рыночные котировки и метрики по списку тикеров.",
    schema: z.object({
      tickerSymbols: z.array(z.string()).min(1),
      fields: z.array(z.string()).min(1),
    }),
  }
);

const marketAgent = createAgent({
  model: new ChatOpenAI({ model: "gpt-4o-mini", temperature: 0 }),
  tools: [financeTickerLookup, financeQuotes],
  systemPrompt: `Ты — финансовый аналитик-ассистент.
1. Если пользователь указал компанию словами, сначала найди тикер через finance_tickers_lookup.
2. Затем получи котировки через finance_quotes.
3. Отвечай по-русски, кратко и структурированно.
4. Не выдумывай числа: используй только данные инструментов.
5. В конце добавь: "Данные носят информационный характер и не являются инвестиционной рекомендацией."`,
});

const result = await marketAgent.invoke({
  messages: [{ role: "user", content: "Какая цена и динамика у AAPL сегодня?" }],
});

console.log(result.messages.at(-1)?.content);
