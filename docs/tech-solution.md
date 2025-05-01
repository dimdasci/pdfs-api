# PDF Structure Analysis Tool – Architecture & API Summary

## 1  Purpose of This Document
This document captures the key architectural and API decisions for the **PDF Structure Analysis Tool** MVP, as agreed with the AWS Solution Architect.  

---

## 2  Product Scope & Value
* **Job‑to‑be‑done:** give engineers visual insight into PDF internals to debug extraction errors.
* **MVP Features**
  * Layer slicer & outliner (text / path / image / etc.).
  * Interactive layer toggles in the browser.
  * Object‑level metadata export.
  * All anomaly detection (zero‑area, repeated patterns) runs **client‑side**.

---

## 3  Architecture Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Frontend** | React SPA on S3 + CloudFront (Origin Access Control) | Secure CDN delivery. |
| **API** | **HTTP API Gateway v2** (not REST) | Cheaper & lower latency for simple routes. |
| **Auth** | Custom JWT Lambda authorizer | Re‑uses existing IdP. |
| **Processing** | Go + pdfium in Fargate, triggered by SQS | Handles heavy raster jobs asynchronously. |
| **Storage** | Private S3 buckets with SSE‑S3 encryption | Keep PDFs & PNGs secure. |
| **DB** | Reuse universal DynamoDB table `(PK, SK)` | Zero extra infra. |
| **Image delivery** | Pre‑signed S3 URLs (TTL ≈ 15 min) | Bucket remains private; browser fetches directly. |

*Deferred post‑MVP:* S3 versioning, DLQ/Step Functions orchestration.

---

## 4  Minimal HTTP API

| Route | Verb | Purpose |
|-------|------|---------|
| `/documents` | **POST** | Upload PDF, return `{document_id, status}`. |
| `/documents` | **GET** | List PDFs (optional `status` filter). |
| `/documents/{docId}` | **GET** | Manifest: page count, sizes, status. |
| `/documents/{docId}/pages/{page}` | **GET** | **Page Bundle** – raster URL, layer URLs, object metadata. |

All routes require `Authorization: Bearer <JWT>`.

### Page Bundle JSON shape

```jsonc
{
  "document_id": "doc_93a1b6f2",
  "page": 1,
  "size": { "width": 612, "height": 792 },
  "full_raster_url": "https://signed‑s3/…/full.png",
  "layers": [
    { "z_index": 1, "type": "path", "url": "https://…/layer‑z01.png", "object_count": 8 },
    { "z_index": 2, "type": "text", "url": "https://…/layer‑z02.png", "object_count": 37 }
  ],
  "objects": [
    { "id": "obj_1", "type": "text", "bbox": [108.0,708.8,115.1,716.7], "z_index": 2 }
  ]
}
```

---

## 5  DynamoDB Universal Schema Patterns

| Entity | PK | SK |
|--------|----|----|
| Document | `USER#<uid>` | `PDF#<docId>` |
| Page | `USER#<uid>` | `PDF#<docId>PAGE#<n>` |

Layer is an element of the Page entity.

Objects JSON is stored in S3; DynamoDB only keeps pointers & counts.

---

## 6  Security Checklist

1. Block public access on all buckets.  
2. Enforce `x‑amz-server-side-encryption: AES256` on uploads.  
3. Generate pre‑signed URLs in Page Bundle Lambda (default TTL 900 s).  
4. Use least‑privilege IAM roles for Fargate & Lambdas.  

---

## 7  Next Steps

| Priority | Task |
|----------|------|
| **P0** | Build Page Bundle Lambda (manifest lookup + presign). |
| **P0** | Implement Fargate worker & S3 key conventions. |
| **P1** | React hook: fetch & cache Page Bundles; refresh on 403. |
| **P2** | Add DLQ + retry metrics. |
| **P2** | Enable S3 versioning & object‑lock (audit). |

---

*Generated 2025‑04‑21.*
