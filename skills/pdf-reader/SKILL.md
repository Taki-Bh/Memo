---
name: pdf-reader
description: This skill should be used when the user asks to read, analyze, summarize, explain, extract, compare, or answer questions about a PDF document, including requests such as "read this PDF", "summarize this PDF", "what does this PDF say?", "extract the key points", "find information in this PDF", or "answer questions from this PDF".
---

# PDF Reader

Read and analyze PDF documents accurately while preserving meaningful document structure and distinguishing extracted information from interpretation.

## Workflow

1. Identify the PDF and determine the user's requested operation.
2. Extract readable text in page order, preserving headings, lists, tables, captions, and other meaningful structure where possible.
3. Check the extracted content for missing, duplicated, corrupted, or out-of-order text.
4. Handle tables as structured data when possible, preserving row and column relationships rather than flattening them into ambiguous prose.
5. Inspect images, charts, diagrams, figures, and other visual content when they contain information relevant to the user's request.
6. Use OCR for scanned or image-only pages when OCR is available. Mark uncertain OCR results as uncertain rather than presenting them as exact text.
7. Base answers on information supported by the PDF unless the user explicitly requests outside information or context.
8. Cite page numbers whenever they can be reliably determined.
9. Preserve important qualifications, definitions, dates, units, conditions, exceptions, and caveats.
10. State clearly when requested information cannot be found instead of inferring or fabricating it.
11. Report significant access limitations, such as an unreadable, incomplete, corrupted, or password-protected PDF, and distinguish unavailable content from content that was successfully read.
12. For summaries, prioritize the document's purpose, main claims, findings, conclusions, recommendations, and actionable details over repetition and minor wording.
13. For long documents, organize findings by section or topic and provide a concise overview before detailed analysis when appropriate.
14. For questions about specific passages, locate the relevant section and answer directly, including the page reference when available.
15. For comparisons involving multiple PDFs, apply the same criteria to each document before identifying similarities, differences, contradictions, and notable omissions.

## Output

Match the response to the requested operation:

- **Summary:** Give a concise overview followed by the key points.
- **Question answering:** Answer directly and provide page references where possible.
- **Information extraction:** Present the requested facts in a clear, structured format.
- **Detailed analysis:** Organize findings by section or topic and distinguish document-supported facts from interpretation.
- **Comparison:** Use consistent criteria and explicitly identify meaningful similarities and differences.
- **Full-text reading:** Preserve the PDF's structure as closely as practical and avoid unnecessary rewriting.

Never fabricate text, page numbers, figures, tables, or conclusions that are not supported by the PDF.