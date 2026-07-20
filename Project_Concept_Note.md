# Project Concept Note

**Title**: ContractSimplifier — AI-Powered Legal Document Analyzer

**Live URL**: http://3.213.82.133

## Problem Statement
Legal and rental contracts are notoriously dense, laden with complex jargon, and difficult for the average person to comprehend. This complexity often leads individuals to inadvertently agree to unfavorable terms or overlook high-risk clauses simply because they cannot afford an expensive lawyer to review every document.

## Target User
Everyday individuals, freelancers, tenants, and small business owners who need to quickly and confidently understand contracts before signing them, without the barrier of expensive legal consultation.

## LLMs & APIs Used
- **Primary**: **Groq API** (utilizing high-speed Llama 3 models like `llama-3.3-70b-versatile`).
- **Fallback**: **Google Gemini API** (utilizing `gemini-2.5-flash` for high availability if rate limits are reached).

## Key Features
- **Flexible Input**: Users can either upload a PDF contract directly or paste raw contract text.
- **Clause-by-Clause Breakdown**: The system automatically splits the contract and analyzes it clause by clause.
- **Plain-English Explanations**: Translates complex legalese into simple, easily understandable language.
- **Risk Rating System**: Highlights potential pitfalls by assigning a risk level (**LOW**, **MEDIUM**, or **HIGH**) to every clause.
- **Overall Verdict**: Provides a comprehensive summary verdict and an overall risk assessment for the entire document.
- **Real-Time Streaming**: Utilizes Server-Sent Events (SSE) to stream results to the user in real-time as the AI processes them.

## Expected UX
A clean, intuitive, and responsive web interface built with React. Users are greeted with a straightforward input area to paste text or upload a document. Upon submission, they experience a dynamic, progressive UI that streams the simplified explanations and color-coded risk ratings live, keeping them engaged and informed without long loading screens.
