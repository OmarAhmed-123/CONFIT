# CONFIT — Complete System Architecture

**Version:** 1.0.0  
**Date:** March 2026  
**Author:** System Architect

---

# Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Service Architecture](#2-service-architecture)
3. [Microservices Design](#3-microservices-design)
4. [API Gateway Design](#4-api-gateway-design)
5. [Database Architecture](#5-database-architecture)
6. [AI Services Architecture](#6-ai-services-architecture)
7. [Security Architecture](#7-security-architecture)
8. [Caching Strategy](#8-caching-strategy)
9. [Search System](#9-search-system)
10. [Scaling Strategy](#10-scaling-strategy)
11. [CI/CD Pipeline](#11-cicd-pipeline)
12. [Observability](#12-observability)
13. [Folder Structure](#13-folder-structure)
14. [Deployment Diagram](#14-deployment-diagram)
15. [Tech Stack Reasoning](#15-tech-stack-reasoning)

---

# 1. High-Level Architecture

## 1.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CONFIT PLATFORM                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │   WEB APP   │    │  MOBILE APP │    │  BRAND      │    │  ADMIN      │       │
│  │  (React +   │    │  (React     │    │  DASHBOARD  │    │  PANEL      │       │
│  │   Vite)     │    │   Native)   │    │             │    │             │       │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘       │
│         │                  │                  │                  │               │
│         └──────────────────┴──────────────────┴──────────────────┘               │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         API GATEWAY (Kong/AWS API Gateway)               │    │
│  │  • Rate Limiting  • Authentication  • Request Routing  • SSL Termination│    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│         ┌────────────────────────────┼────────────────────────────┐             │
│         │                            │                            │             │
│         ▼                            ▼                            ▼             │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐          │
│  │  CORE API   │            │  AI SERVICES│            │  WORKERS    │          │
│  │  (FastAPI)  │            │  (FastAPI)  │            │  (Celery)   │          │
│  │             │            │             │            │             │          │
│  │ • Auth      │            │ • Try-On    │            │ • Image     │          │
│  │ • Users     │            │ • Stylist   │            │   Processing│          │
│  │ • Products  │            │ • Visual    │            │ • Analytics │          │
│  │ • Orders    │            │   Search    │            │ • Notifications        │
│  │ • Wardrobe  │            │ • Outfit    │            │ • ML Jobs   │          │
│  │ • Payments  │            │   Builder   │            │             │          │
│  └──────┬──────┘            └──────┬──────┘            └──────┬──────┘          │
│         │                          │                          │                 │
│         └──────────────────────────┴──────────────────────────┘                 │
│                                      │                                           │
│         ┌────────────────────────────┼────────────────────────────┐             │
│         │                            │                            │             │
│         ▼                            ▼                            ▼             │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐          │
│  │ PostgreSQL  │            │   Redis     │            │ Elasticsearch│         │
│  │  (Primary)  │            │  (Cache)    │            │  (Search)   │          │
│  └─────────────┘            └─────────────┘            └─────────────┘          │
│                                                                                  │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐          │
│  │   S3/MinIO  │            │  Message    │            │ Monitoring  │          │
│  │  (Storage)  │            │  Queue      │            │ (Prometheus)│          │
│  └─────────────┘            └─────────────┘            └─────────────┘          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Domain-Driven Design** | Bounded contexts per feature group |
| **Clean Architecture** | Layers: API → Application → Domain → Infrastructure |
| **Event-Driven** | Async communication via message queues |
| **CQRS** | Separate read/write paths for high-traffic features |
| **Microservices** | Independent deployable services |
| **API-First** | OpenAPI specs before implementation |

## 1.3 Bounded Contexts (DDD)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BOUNDED CONTEXTS MAP                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐        │
│  │ IDENTITY CONTEXT │  │ STYLING CONTEXT  │  │ VISUALIZATION    │        │
│  │                  │  │                  │  │    CONTEXT       │        │
│  │ • User Profile   │  │ • Virtual Stylist│  │ • Virtual Try-On │        │
│  │ • Style Profile  │  │ • Outfit Builder │  │ • Digital Twin   │        │
│  │ • Body Profile   │  │ • Wardrobe       │  │ • Visual Search  │        │
│  │ • Preferences    │  │ • AI Brain       │  │ • 360° Rotation  │        │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘        │
│           │                     │                     │                 │
│           └─────────────────────┼─────────────────────┘                 │
│                                 │                                        │
│  ┌──────────────────┐  ┌───────▼──────────┐  ┌──────────────────┐        │
│  │ MARKETPLACE      │  │ COMMERCE CONTEXT │  │ BRAND CONTEXT    │        │
│  │    CONTEXT       │  │                  │  │                  │        │
│  │                  │  │ • Orders         │  │ • Brand Dashboard│        │
│  │ • Products       │  │ • Payments       │  │ • Analytics      │        │
│  │ • Catalog        │  │ • Checkout       │  │ • Inventory      │        │
│  │ • Search         │  │ • BNPL           │  │ • Store Locator  │        │
│  │ • BOPIS          │  │ • Fulfillment    │  │ • BOPIS          │        │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 2. Service Architecture

## 2.1 Core API Services (FastAPI Monolith)

The main backend is organized as a modular monolith with clear bounded context separation:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CORE API (FastAPI)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      API LAYER (Routers)                         │    │
│  │  /auth  /users  /products  /orders  /wardrobe  /stylist  /try-on │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   APPLICATION LAYER (Services)                  │    │
│  │  Auth   User   Product   Order   Wardrobe   Stylist   TryOn     │    │
│  │  Service Service Service Service  Service   Service  Service    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      DOMAIN LAYER (Models)                       │    │
│  │   User   Product   Order   Wardrobe   Outfit   DigitalTwin      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                  INFRASTRUCTURE LAYER                            │    │
│  │  Database  Cache  Storage  Queue  External APIs  Logging        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Service Catalog

| Service | Port | Responsibilities | Dependencies |
|---------|------|------------------|--------------|
| **auth-service** | 8001 | JWT auth, OAuth2, session management | PostgreSQL, Redis |
| **user-service** | 8002 | Profile, preferences, body profile | PostgreSQL |
| **product-service** | 8003 | Catalog, inventory, pricing | PostgreSQL, Elasticsearch |
| **order-service** | 8004 | Orders, checkout, fulfillment | PostgreSQL, Stripe |
| **wardrobe-service** | 8005 | Virtual wardrobe, tagging | PostgreSQL, S3 |
| **stylist-service** | 8006 | AI recommendations, outfits | PostgreSQL, AI Services |
| **try-on-service** | 8007 | Virtual try-on processing | S3, AI Services |
| **search-service** | 8008 | Full-text, visual search | Elasticsearch, AI Services |
| **payment-service** | 8009 | Stripe, BNPL integration | PostgreSQL, Stripe |
| **notification-service** | 8010 | Email, push, SMS | Redis, SQS |

## 2.3 Inter-Service Communication

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SERVICE COMMUNICATION PATTERNS                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SYNCHRONOUS (HTTP/REST)                                                 │
│  ┌─────────┐      GET /users/{id}      ┌─────────┐                       │
│  │ Order   │ ─────────────────────────▶│  User   │                       │
│  │ Service │ ◀─────────────────────────│ Service │                       │
│  └─────────┘      User Profile JSON    └─────────┘                       │
│                                                                          │
│  ASYNCHRONOUS (Message Queue)                                           │
│  ┌─────────┐      OrderCreatedEvent    ┌─────────┐                       │
│  │ Order   │ ─────────────────────────▶│  Redis  │                       │
│  │ Service │                           │  Pub/Sub│                       │
│  └─────────┘                           └────┬────┘                       │
│                                             │                            │
│                    ┌────────────────────────┼────────────────────────┐   │
│                    │                        │                        │   │
│                    ▼                        ▼                        ▼   │
│             ┌──────────┐            ┌──────────┐            ┌──────────┐ │
│             │ Notif    │            │ Analytics│            │ Inventory│ │
│             │ Service  │            │ Service  │            │ Service  │ │
│             └──────────┘            └──────────┘            └──────────┘ │
│                                                                          │
│  EVENT STREAMING (Real-time)                                            │
│  ┌─────────┐      WebSocket/SSE      ┌─────────┐                        │
│  │ Stylist │ ◀──────────────────────▶│  User   │                        │
│  │ Service │   Real-time Updates    │  Client │                        │
│  └─────────┘                         └─────────┘                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 3. Microservices Design

## 3.1 AI Microservices (GPU-Enabled)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI MICROSERVICES                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    VIRTUAL TRY-ON SERVICE                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │  │
│  │  │ Pose        │→ │ Garment     │→ │ Image       │                │  │
│  │  │ Estimation  │  │ Overlay     │  │ Synthesis   │                │  │
│  │  │ (MediaPipe) │  │ (OpenCV)    │  │ (Diffusion) │                │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │  │
│  │  Port: 9001 | GPU: Required | Model: SD + ControlNet             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    VIRTUAL STYLIST SERVICE                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │  │
│  │  │ Style       │→ │ Context     │→ │ LLM         │                │  │
│  │  │ Analysis    │  │ Builder     │  │ Generation  │                │  │
│  │  │ (Embedding) │  │ (RAG)       │  │ (Groq/Llama)│                │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │  │
│  │  Port: 9002 | GPU: Optional | Model: Llama 3 + RAG                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    VISUAL SEARCH SERVICE                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │  │
│  │  │ Image       │→ │ Feature     │→ │ Vector      │                │  │
│  │  │ Processing  │  │ Extraction  │  │ Search      │                │  │
│  │  │ (Preprocess)│  │ (CLIP/ViT)  │  │ (Milvus)    │                │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │  │
│  │  Port: 9003 | GPU: Required | Model: CLIP + Vector DB             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    OUTFIT BUILDER SERVICE                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │  │
│  │  │ Item        │→ │ Compatibility│→ │ Scoring     │                │  │
│  │  │ Embedding   │  │ Matrix      │  │ & Ranking   │                │  │
│  │  │ (CLIP)      │  │             │  │             │                │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │  │
│  │  Port: 9004 | GPU: Optional | Model: CLIP + Custom                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    DIGITAL TWIN SERVICE                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │  │
│  │  │ Body Scan   │→ │ 3D Model    │→ │ Avatar      │                │  │
│  │  │ Processing  │  │ Generation  │  │ Rendering   │                │  │
│  │  │             │  │ (SMPL)      │  │ (Three.js)  │                │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │  │
│  │  Port: 9005 | GPU: Required | Model: SMPL + Custom                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Background Workers (Celery)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CELERY WORKERS                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  IMAGE PROCESSING WORKER                                          │  │
│  │  • Image resize/compression for products                          │  │
│  │  • Thumbnail generation                                           │  │
│  │  • Background removal                                             │  │
│  │  Queue: image_tasks | Concurrency: 4                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  ANALYTICS WORKER                                                 │  │
│  │  • Aggregating user behavior metrics                              │  │
│  │  • Generating brand reports                                       │  │
│  │  • Computing recommendation scores                                │  │
│  │  Queue: analytics_tasks | Concurrency: 2                          │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  NOTIFICATION WORKER                                              │  │
│  │  • Email sending (SendGrid/AWS SES)                               │  │
│  │  • Push notifications (Firebase)                                  │  │
│  │  • SMS alerts (Twilio)                                            │  │
│  │  Queue: notification_tasks | Concurrency: 8                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  ML TRAINING WORKER                                               │  │
│  │  • Fine-tuning style models                                       │  │
│  │  • Updating recommendation embeddings                             │  │
│  │  • Retraining visual search index                                 │  │
│  │  Queue: ml_tasks | Concurrency: 1 (GPU)                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 4. API Gateway Design

## 4.1 Gateway Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (Kong / AWS API Gateway)              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     SECURITY LAYER                               │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │    │
│  │  │   SSL    │  │   JWT    │  │   OAuth  │  │   API    │        │    │
│  │  │Termination│  │Validation│  │  2.0    │  │   Keys   │        │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     TRAFFIC LAYER                                │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │    │
│  │  │   Rate   │  │  Request │  │  Load    │  │ Circuit  │        │    │
│  │  │ Limiting │  │Transform │  │ Balancing│  │ Breaker  │        │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     ROUTING LAYER                                │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │  /api/v1/auth/*     → auth-service:8001                  │   │    │
│  │  │  /api/v1/users/*    → user-service:8002                  │   │    │
│  │  │  /api/v1/products/* → product-service:8003               │   │    │
│  │  │  /api/v1/orders/*   → order-service:8004                 │   │    │
│  │  │  /api/v1/wardrobe/* → wardrobe-service:8005              │   │    │
│  │  │  /api/v1/stylist/*  → stylist-service:8006               │   │    │
│  │  │  /api/v1/try-on/*   → try-on-service:8007                │   │    │
│  │  │  /api/v1/search/*   → search-service:8008                │   │    │
│  │  │  /api/v1/payments/* → payment-service:8009               │   │    │
│  │  │  /ai/*              → ai-gateway:9000                   │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     OBSERVABILITY LAYER                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │    │
│  │  │  Access  │  │  Metrics │  │  Tracing │  │  Error   │        │    │
│  │  │   Logs   │  │ Export   │  │   (X-Ray)│  │ Tracking │        │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 4.2 API Route Definitions

### Core API Routes

| Route | Method | Service | Description |
|-------|--------|---------|-------------|
| `/api/v1/auth/register` | POST | auth | User registration |
| `/api/v1/auth/login` | POST | auth | JWT token generation |
| `/api/v1/auth/oauth/{provider}` | GET | auth | OAuth redirect |
| `/api/v1/auth/oauth/callback` | GET | auth | OAuth callback |
| `/api/v1/auth/refresh` | POST | auth | Token refresh |
| `/api/v1/users/me` | GET/PUT | user | Profile management |
| `/api/v1/users/me/style` | PUT | user | Style preferences |
| `/api/v1/users/me/body` | PUT | user | Body profile |
| `/api/v1/products` | GET | product | Product listing |
| `/api/v1/products/{id}` | GET | product | Product details |
| `/api/v1/products/search` | GET | search | Search products |
| `/api/v1/orders` | GET/POST | order | Order management |
| `/api/v1/orders/checkout` | POST | order | Checkout process |
| `/api/v1/wardrobe` | GET/POST | wardrobe | Wardrobe items |
| `/api/v1/wardrobe/{id}/tag` | POST | wardrobe | Auto-tagging |

### AI Service Routes

| Route | Method | Service | Description |
|-------|--------|---------|-------------|
| `/ai/try-on` | POST | try-on | Virtual try-on request |
| `/ai/try-on/{id}/status` | GET | try-on | Processing status |
| `/ai/stylist/recommend` | POST | stylist | Get recommendations |
| `/ai/stylist/chat` | POST | stylist | Chat with stylist |
| `/ai/visual-search` | POST | search | Search by image |
| `/ai/outfit/build` | POST | outfit | Generate outfit |
| `/ai/digital-twin/create` | POST | twin | Create body model |

## 4.3 Rate Limiting Configuration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      RATE LIMITING TIERS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  TIER 1: PUBLIC ENDPOINTS                                         │  │
│  │  • /api/v1/products/*    → 100 req/min                           │  │
│  │  • /api/v1/search/*      → 60 req/min                            │  │
│  │  • /api/v1/auth/login    → 10 req/min (per IP)                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  TIER 2: AUTHENTICATED ENDPOINTS                                  │  │
│  │  • /api/v1/users/*       → 200 req/min                           │  │
│  │  • /api/v1/orders/*      → 100 req/min                           │  │
│  │  • /api/v1/wardrobe/*    → 150 req/min                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  TIER 3: AI ENDPOINTS (GPU-intensive)                             │  │
│  │  • /ai/try-on            → 10 req/min                           │  │
│  │  • /ai/stylist/*         → 30 req/min                            │  │
│  │  • /ai/visual-search     → 20 req/min                            │  │
│  │  • /ai/digital-twin/*    → 5 req/min                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  TIER 4: BRAND/ADMIN ENDPOINTS                                    │  │
│  │  • /api/v1/brand/*       → 500 req/min                           │  │
│  │  • /api/v1/admin/*       → 300 req/min                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 5. Database Architecture

## 5.1 Database Per Bounded Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATABASE ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    PRIMARY DATABASE CLUSTER                        │  │
│  │                    (PostgreSQL 16 + Citus)                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │  IDENTITY   │  │  COMMERCE   │  │  CONTENT    │               │  │
│  │  │    DB       │  │    DB       │  │    DB       │               │  │
│  │  │             │  │             │  │             │               │  │
│  │  │ • users     │  │ • orders    │  │ • wardrobe  │               │  │
│  │  │ • profiles  │  │ • payments  │  │ • outfits   │               │  │
│  │  │ • auth      │  │ • cart      │  │ • digital   │               │  │
│  │  │             │  │             │  │   twins     │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  │                                                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │  CATALOG    │  │   BRAND     │  │  ANALYTICS  │               │  │
│  │  │    DB       │  │    DB       │  │    DB       │               │  │
│  │  │             │  │             │  │             │               │  │
│  │  │ • products  │  │ • brands    │  │ • events    │               │  │
│  │  │ • inventory │  │ • stores    │  │ • metrics   │               │  │
│  │  │ • categories│  │ • campaigns │  │ • reports   │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    READ REPLICAS                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  • catalog-read-replica-1 (products, search)                │  │  │
│  │  │  • analytics-read-replica-1 (reports, dashboards)           │  │  │
│  │  │  • identity-read-replica-1 (user profiles)                  │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 5.2 Core Entity Schema

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ENTITY RELATIONSHIP DIAGRAM                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐           │
│  │    USER     │       │    BRAND    │       │    STORE    │           │
│  ├─────────────┤       ├─────────────┤       ├─────────────┤           │
│  │ id (UUID)   │       │ id (UUID)   │       │ id (UUID)   │           │
│  │ email       │       │ name        │       │ brand_id FK │           │
│  │ name        │       │ slug        │       │ name        │           │
│  │ password_h  │       │ logo_url    │       │ address     │           │
│  │ style_pref  │       │ description │       │ coords      │           │
│  │ body_profile│       │ is_verified │       │ is_active   │           │
│  │ budget_range│       └──────┬──────┘       └──────┬──────┘           │
│  └──────┬──────┘              │                     │                 │
│         │                     │                     │                 │
│         │    ┌────────────────┴─────────────────────┘                 │
│         │    │                                                        │
│         ▼    ▼                                                        │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐           │
│  │   PRODUCT   │       │    ORDER    │       │ ORDER_ITEM  │           │
│  ├─────────────┤       ├─────────────┤       ├─────────────┤           │
│  │ id (UUID)   │       │ id (UUID)   │       │ id (UUID)   │           │
│  │ brand_id FK │       │ user_id FK  │       │ order_id FK │           │
│  │ name        │       │ status      │       │ product_id  │           │
│  │ description │       │ total       │       │ quantity    │           │
│  │ price       │       │ created_at  │       │ price       │           │
│  │ category    │       │ updated_at  │       │ size        │           │
│  │ images[]    │       └─────────────┘       └─────────────┘           │
│  │ sizes[]     │                                                      │
│  │ tags[]      │                                                      │
│  └──────┬──────┘                                                      │
│         │                                                             │
│         ├────────────────────┬────────────────────┐                    │
│         │                    │                    │                    │
│         ▼                    ▼                    ▼                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                    │
│  │WARDROBE_ITEM│  │   OUTFIT    │  │DIGITAL_TWIN │                    │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤                    │
│  │ id (UUID)   │  │ id (UUID)   │  │ id (UUID)   │                    │
│  │ user_id FK  │  │ user_id FK  │  │ user_id FK  │                    │
│  │ product_id  │  │ name        │  │ model_url   │                    │
│  │ custom_img  │  │ items[]     │  │ measurements│                    │
│  │ tags[]      │  │ occasion    │  │ pose_data   │                    │
│  │ worn_count  │  │ season      │  │ created_at  │                    │
│  └─────────────┘  └─────────────┘  └─────────────┘                    │
│                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## 5.3 Data Flow Patterns

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA FLOW PATTERNS                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  WRITE PATH (Command)                                                    │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│  │ Client  │───▶│  API    │───▶│ Service │───▶│   DB    │               │
│  │ Request │    │ Gateway │    │ Layer   │    │ Primary │               │
│  └─────────┘    └─────────┘    └─────────┘    └────┬────┘               │
│                                                    │                     │
│                    ┌───────────────────────────────┘                    │
│                    │                                                │
│                    ▼                                                │
│               ┌─────────┐    ┌─────────┐                            │
│               │  Event  │───▶│  Cache  │ (Invalidate)               │
│               │  Queue  │    │  Redis  │                            │
│               └─────────┘    └─────────┘                            │
│                                                                        │
│  READ PATH (Query)                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│  │ Client  │───▶│  API    │───▶│ Service │───▶│  Cache  │ HIT          │
│  │ Request │    │ Gateway │    │ Layer   │    │  Redis  │───▶ Response  │
│  └─────────┘    └─────────┘    └─────────┘    └────┬────┘               │
│                                                    │ MISS              │
│                    ┌───────────────────────────────┘                    │
│                    ▼                                                │
│               ┌─────────┐    ┌─────────┐                            │
│               │   DB    │───▶│  Cache  │ (Populate)                  │
│               │ Replica │    │  Redis  │                            │
│               └─────────┘    └─────────┘                            │
│                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 6. AI Services Architecture

## 6.1 AI Service Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AI SERVICES INTEGRATION                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    AI SERVICE ORCHESTRATOR                        │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  • Request Queue Management                                  │  │  │
│  │  │  • GPU Resource Scheduling                                  │  │  │
│  │  │  • Model Versioning & A/B Testing                           │  │  │
│  │  │  • Fallback & Degradation Handling                          │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    MODEL SERVING LAYER                            │  │
│  │                                                                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │  Local   │  │  Hugging │  │   Groq   │  │  OpenAI  │        │  │
│  │  │  Models  │  │  Face    │  │  Cloud   │  │   API    │        │  │
│  │  │ (GPU)    │  │  Inference│  │ (LLM)   │  │ (GPT-4)  │        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  │                                                                    │  │
│  │  Models:                                                          │  │
│  │  • Stable Diffusion + ControlNet (Try-On)                        │  │
│  │  • Llama 3 70B (Stylist Chat)                                    │  │
│  │  • CLIP ViT-L/14 (Visual Search, Embeddings)                     │  │
│  │  • SMPL Body Model (Digital Twin)                                │  │
│  │  • MediaPipe Pose (Pose Estimation)                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    VECTOR DATABASE (Milvus/Qdrant)                 │  │
│  │  • Product embeddings (CLIP)                                     │  │
│  │  • Style profile vectors                                         │  │
│  │  • Outfit compatibility matrices                                 │  │
│  │  • Visual search index                                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 6.2 AI Request Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    VIRTUAL TRY-ON PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User Photo  ──▶  Preprocessing  ──▶  Pose Detection  ──▶  Segmentation  │
│                       │                    │                    │        │
│                       ▼                    ▼                    ▼        │
│                  Resize/Normalize    MediaPipe Pose    Body Mask Gen    │
│                                                                          │
│  Garment Image ──▶  Preprocessing ──▶  Feature Extract ──▶  Warp        │
│                           │                    │              │        │
│                           ▼                    ▼              ▼        │
│                      Remove BG         CLIP Embedding    Geometry Align │
│                                                                          │
│  Combined ──▶  Diffusion Model ──▶  Post-Processing ──▶  Result        │
│                    │                    │                    │          │
│                    ▼                    ▼                    ▼          │
│              SD + ControlNet       Color Correction    Upload to S3    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    VIRTUAL STYLIST PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User Context ──▶  Profile Analysis  ──▶  Context Builder  ──▶  RAG     │
│       │                  │                    │               │          │
│       ▼                  ▼                    ▼               ▼          │
│  Style/Budget       Extract         Build Prompt      Retrieve         │
│  Preferences        Preferences      with Context      Similar Items    │
│                                                                          │
│  ──▶  LLM Generation  ──▶  Response Parser  ──▶  Product Matching      │
│            │                    │                    │                  │
│            ▼                    ▼                    ▼                  │
│       Llama 3 / Groq     Parse JSON        Link to Catalog             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 6.3 Fallback Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AI FALLBACK CHAIN                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  VIRTUAL STYLIST:                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  1. Groq Cloud (Llama 3 70B) ──▶ Fast, cheap                     │   │
│  │  2. OpenAI GPT-4 ──▶ Backup, higher quality                      │   │
│  │  3. Local Llama 3 ──▶ Offline fallback                           │   │
│  │  4. Rule-based Recommender ──▶ No AI, deterministic             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  VIRTUAL TRY-ON:                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  1. Local SD + ControlNet ──▶ Best quality, GPU required        │   │
│  │  2. HuggingFace Inference API ──▶ Cloud fallback                 │   │
│  │  3. Simple Overlay (OpenCV) ──▶ Basic visualization              │   │
│  │  4. 2D Mannequin Render ──▶ No body mapping                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  VISUAL SEARCH:                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  1. Local CLIP + Milvus ──▶ Fast, accurate                       │   │
│  │  2. Elasticsearch Text Search ──▶ Keyword fallback               │   │
│  │  3. Category Browse ──▶ Manual navigation                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 7. Security Architecture

## 7.1 Security Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SECURITY ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LAYER 1: NETWORK SECURITY                                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  • WAF (Web Application Firewall)                                 │  │
│  │  • DDoS Protection (CloudFlare/AWS Shield)                        │  │
│  │  • VPC Isolation                                                   │  │
│  │  • Security Groups / NACLs                                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  LAYER 2: TRANSPORT SECURITY                                            │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  • TLS 1.3 Enforcement                                            │  │
│  │  • HSTS Headers                                                    │  │
│  │  • Certificate Pinning (Mobile)                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  LAYER 3: AUTHENTICATION                                                │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  • JWT Access Tokens (15 min expiry)                              │  │
│  │  • Refresh Tokens (7 days, stored in Redis)                       │  │
│  │  • OAuth 2.0 (Google, Apple, Facebook)                            │  │
│  │  • Multi-Factor Auth (TOTP, SMS)                                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  LAYER 4: AUTHORIZATION                                                 │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  • Role-Based Access Control (RBAC)                               │  │
│  │    - USER: Personal data, orders, wardrobe                        │  │
│  │    - BRAND: Product management, analytics                         │  │
│  │    - ADMIN: System management, user management                    │  │
│  │  • Resource-Level Permissions                                     │  │
│  │  • API Scopes (read:profile, write:wardrobe, etc.)                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  LAYER 5: DATA SECURITY                                                 │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  • Encryption at Rest (AES-256)                                  │  │
│  │  • Encryption in Transit (TLS)                                    │  │
│  │  • Field-Level Encryption (PII)                                   │  │
│  │  • Key Management (AWS KMS)                                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  LAYER 6: APPLICATION SECURITY                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  • Input Validation & Sanitization                                │  │
│  │  • SQL Injection Prevention (Parameterized Queries)              │  │
│  │  • XSS Prevention (CSP Headers)                                   │  │
│  │  • CSRF Protection (Double Submit Cookie)                         │  │
│  │  • Rate Limiting                                                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 7.2 Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      JWT AUTHENTICATION FLOW                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LOGIN FLOW:                                                            │
│                                                                          │
│  ┌─────────┐    POST /auth/login    ┌─────────┐                          │
│  │  Client │ ─────────────────────▶│  API    │                          │
│  │         │    {email, password}  │ Gateway │                          │
│  └─────────┘                        └────┬────┘                          │
│                                          │                               │
│                                          ▼                               │
│                                    ┌─────────┐                          │
│                                    │  Auth   │                          │
│                                    │ Service │                          │
│                                    └────┬────┘                          │
│                                         │                                │
│                    ┌────────────────────┼────────────────────┐           │
│                    │                    │                    │           │
│                    ▼                    ▼                    ▼           │
│              ┌──────────┐        ┌──────────┐        ┌──────────┐       │
│              │ Validate │        │ Generate │        │  Store   │       │
│              │ Password │        │   JWT    │        │ Refresh  │       │
│              │  (bcrypt)│        │  + Refresh│        │ in Redis │       │
│              └──────────┘        └──────────┘        └──────────┘       │
│                                                                         │
│                                    ┌─────────┐                          │
│  ┌─────────┐   {access_token,      │  Auth   │                          │
│  │  Client │◀──refresh_token}─────│ Service │                          │
│  └─────────┘                       └─────────┘                          │
│                                                                          │
│  TOKEN REFRESH FLOW:                                                    │
│                                                                          │
│  ┌─────────┐  POST /auth/refresh  ┌─────────┐                           │
│  │  Client │ ───────────────────▶│  Auth   │                           │
│  │         │  {refresh_token}    │ Service │                           │
│  └─────────┘                     └────┬────┘                           │
│                                       │                                 │
│                                       ▼                                 │
│                                 ┌──────────┐                           │
│                                 │  Verify  │                           │
│                                 │ Refresh  │                           │
│                                 │ in Redis │                           │
│                                 └────┬─────┘                           │
│                                      │                                  │
│                                      ▼                                  │
│                                 ┌──────────┐                           │
│                                 │  Rotate  │                           │
│                                 │  Tokens  │                           │
│                                 └────┬─────┘                           │
│                                      │                                  │
│  ┌─────────┐  {new_access,       ┌────┴────┐                           │
│  │  Client │◀──new_refresh}─────│  Auth   │                           │
│  └─────────┘                     │ Service │                           │
│                                  └─────────┘                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 7.3 OAuth 2.0 Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      OAUTH 2.0 FLOW                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────┐  GET /auth/oauth/google  ┌─────────┐  ┌─────────┐          │
│  │  User   │ ───────────────────────▶│  CONFIT │  │  Google │          │
│  │ Browser │                         │  API    │  │  OAuth  │          │
│  └─────────┘                         └────┬────┘  └────┬────┘          │
│       │                                   │            │                │
│       │◀─────────── Redirect to Google ───┼────────────┘                │
│       │                                   │                             │
│       │  ──── Authorize on Google ───────▶│                             │
│       │                                   │                             │
│       │◀─────── Redirect with code ───────┤                             │
│       │       /auth/oauth/callback?code=  │                             │
│       │                                   │                             │
│       │  ──── GET /callback?code= ──────▶│                             │
│       │                                   │                             │
│       │                        ┌──────────┴──────────┐                  │
│       │                        │                     │                  │
│       │                        ▼                     ▼                  │
│       │                  ┌──────────┐         ┌──────────┐             │
│       │                  │ Exchange │         │ Get User │             │
│       │                  │   Code   │         │  Profile │             │
│       │                  │for Token │         │          │             │
│       │                  └──────────┘         └──────────┘             │
│       │                        │                     │                  │
│       │                        └──────────┬──────────┘                  │
│       │                                   │                             │
│       │                        ┌──────────┴──────────┐                  │
│       │                        │                     │                  │
│       │                        ▼                     ▼                  │
│       │                  ┌──────────┐         ┌──────────┐             │
│       │                  │ Find/Create        │ Generate │             │
│       │                  │   User   │         │   JWT    │             │
│       │                  └──────────┘         └──────────┘             │
│       │                                   │                             │
│       │◀─────── Set JWT Cookie ────────────┤                             │
│       │      Redirect to Dashboard         │                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 8. Caching Strategy

## 8.1 Cache Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CACHING ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    LAYER 1: CDN CACHE (CloudFlare/AWS CloudFront)  │  │
│  │  • Static assets (JS, CSS, images)                               │  │
│  │  • Product images (S3 backed)                                    │  │
│  │  • TTL: 30 days                                                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    LAYER 2: API GATEWAY CACHE                      │  │
│  │  • Public product listings                                       │  │
│  │  • Category pages                                                │  │
│  │  • TTL: 5 minutes                                                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    LAYER 3: APPLICATION CACHE (Redis)              │  │
│  │  • User sessions                                                 │  │
│  │  • Product catalog                                               │  │
│  │  • Search results                                                │  │
│  │  • AI recommendations                                            │  │
│  │  • Rate limit counters                                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    LAYER 4: DATABASE CACHE (PostgreSQL)            │  │
│  │  • Query result cache                                            │  │
│  │  • Materialized views                                            │  │
│  │  • Connection pooling (PgBouncer)                                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 8.2 Cache Invalidation Patterns

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CACHE INVALIDATION STRATEGIES                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PATTERN 1: WRITE-THROUGH                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Used for: User profiles, preferences                            │   │
│  │  Flow: Write to DB → Update Cache → Return Success               │   │
│  │  Pros: Data consistency, read performance                        │   │
│  │  Cons: Write latency                                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  PATTERN 2: WRITE-BEHIND (Async)                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Used for: Analytics, metrics, non-critical data                │   │
│  │  Flow: Write to Cache → Return Success → Async write to DB      │   │
│  │  Pros: Low write latency                                         │   │
│  │  Cons: Potential data loss                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  PATTERN 3: CACHE-ASIDE (Lazy Loading)                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Used for: Product catalog, search results                       │   │
│  │  Flow: Check Cache → If miss, load from DB → Cache it            │   │
│  │  Pros: Only caches requested data                                │   │
│  │  Cons: Cache miss penalty                                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  PATTERN 4: TIME-BASED EXPIRATION                                       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Used for: AI recommendations, trending items                    │   │
│  │  TTL: 5-60 minutes depending on data type                        │   │
│  │  Pros: Simple, automatic refresh                                 │   │
│  │  Cons: Stale data possible                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 8.3 Cache Key Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CACHE KEY NAMING CONVENTION                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Format: {namespace}:{entity}:{id}:{version}                            │
│                                                                          │
│  Examples:                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  user:profile:123:v1              → User profile data            │   │
│  │  user:style:123:v1                → User style preferences      │   │
│  │  product:detail:456:v2            → Product detail page          │   │
│  │  product:list:category:dresses:v1 → Category listing              │   │
│  │  search:result:query_hash:v1      → Search results                │   │
│  │  ai:recommend:user:123:v1         → AI recommendations            │   │
│  │  ai:tryon:task:789:v1             → Try-on result                 │   │
│  │  session:refresh:user:123         → Refresh token                 │   │
│  │  rate:limit:ip:192.168.1.1        → Rate limit counter            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  TTL Configuration:                                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • User sessions: 7 days                                         │   │
│  │  • Product catalog: 1 hour                                       │   │
│  │  • Search results: 5 minutes                                     │   │
│  │  • AI recommendations: 30 minutes                                │   │
│  │  • Try-on results: 24 hours                                      │   │
│  │  • Rate limit counters: 1 minute                                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 9. Search System

## 9.1 Search Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SEARCH ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    SEARCH ORCHESTRATOR                             │  │
│  │  • Query parsing & normalization                                  │  │
│  │  • Multi-index routing                                            │  │
│  │  • Result aggregation & ranking                                   │  │
│  │  • Facet computation                                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    SEARCH INDEXES                                  │  │
│  │                                                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │  TEXT INDEX │  │ VECTOR INDEX│  │ FACET INDEX │               │  │
│  │  │ (Elastic)   │  │ (Milvus)    │  │ (Elastic)   │               │  │
│  │  │             │  │             │  │             │               │  │
│  │  │ • Products  │  │ • Embeddings│  │ • Brands    │               │  │
│  │  │ • Brands    │  │ • Images    │  │ • Categories│               │  │
│  │  │ • Tags      │  │ • Styles    │  │ • Sizes     │               │  │
│  │  │ • Desc      │  │             │  │ • Colors    │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    SEARCH FEATURES                                 │  │
│  │  • Full-text search (Elasticsearch)                              │  │
│  │  • Visual search (CLIP + Vector DB)                              │  │
│  │  • Autocomplete & suggestions                                    │  │
│  │  • Fuzzy matching & typo tolerance                               │  │
│  │  • Relevance ranking (BM25 + ML)                                 │  │
│  │  • Personalized results (user style profile)                     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 9.2 Search Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SEARCH REQUEST FLOW                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TEXT SEARCH:                                                           │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│  │  Query  │───▶│  Parse  │───▶│  Text   │───▶│  Rank   │               │
│  │  Input  │    │  & Norm │    │ Search  │    │ Results │               │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘               │
│                      │              │              │                     │
│                      ▼              ▼              ▼                     │
│                Tokenize       Elastic BM25   Personalize               │
│                Stemming       Fuzzy Match    Boost by Style            │
│                                                                          │
│  VISUAL SEARCH:                                                         │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│  │  Image  │───▶│ Preproc │───▶│  CLIP   │───▶│ Vector  │               │
│  │  Input  │    │         │    │ Embed   │    │ Search  │               │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘               │
│                      │              │              │                     │
│                      ▼              ▼              ▼                     │
│                Resize/Norm     512-dim vec    Milvus KNN               │
│                Remove BG      Vision Encoder  Cosine Sim               │
│                                                                          │
│  HYBRID SEARCH (Text + Visual):                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  1. Get text results (BM25 score)                                 │   │
│  │  2. Get visual results (vector similarity)                        │   │
│  │  3. Reciprocal Rank Fusion (RRF)                                 │   │
│  │  4. Apply personalization boost                                  │   │
│  │  5. Return unified ranked list                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 9.3 Index Synchronization

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      INDEX SYNC STRATEGY                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  REAL-TIME SYNC (Critical Data):                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Product Created/Updated → Immediate index update                │   │
│  │  Price Change → Immediate index update                           │   │
│  │  Inventory Change → Immediate index update                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  NEAR-REAL-TIME SYNC (5 min delay):                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Product embeddings → Batch update every 5 min                   │   │
│  │  Style vectors → Batch update every 5 min                        │   │
│  │  Category mappings → Batch update every 5 min                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  SCHEDULED REBUILD (Daily):                                             │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Full index rebuild at 3 AM UTC                                  │   │
│  │  Embedding regeneration for all products                         │   │
│  │  Facet statistics recalculation                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 10. Scaling Strategy

## 10.1 Horizontal Scaling

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      HORIZONTAL SCALING                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  AUTO-SCALING CONFIGURATION                                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  CORE API (CPU-bound):                                            │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  Min: 2 instances | Max: 20 instances                        │  │  │
│  │  │  Scale-up: CPU > 70% for 2 min                               │  │  │
│  │  │  Scale-down: CPU < 30% for 5 min                             │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  AI SERVICES (GPU-bound):                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  Min: 1 GPU instance | Max: 10 GPU instances                 │  │  │
│  │  │  Scale-up: Queue depth > 10 for 1 min                        │  │  │
│  │  │  Scale-down: Queue depth < 2 for 10 min                      │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  WORKERS (I/O-bound):                                             │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  Min: 2 instances | Max: 50 instances                         │  │  │
│  │  │  Scale-up: Queue depth > 100 for 2 min                       │  │  │
│  │  │  Scale-down: Queue depth < 10 for 5 min                       │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 10.2 Database Scaling

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATABASE SCALING                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  READ SCALING (Replicas):                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Primary (Writes)                                                │   │
│  │     │                                                             │   │
│  │     ├──▶ Read Replica 1 (Product catalog queries)                │   │
│  │     ├──▶ Read Replica 2 (User profile queries)                   │   │
│  │     ├──▶ Read Replica 3 (Analytics queries)                      │   │
│  │     └──▶ Read Replica 4 (Search indexing)                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  WRITE SCALING (Sharding):                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Citus (PostgreSQL Extension) for distributed queries            │   │
│  │                                                                    │   │
│  │  Sharding Key Strategy:                                           │   │
│  │  • Users: Shard by user_id (hash distribution)                   │   │
│  │  • Orders: Shard by user_id (co-located with users)              │   │
│  │  • Products: Shard by brand_id                                    │   │
│  │  • Analytics: Time-series partitioning by date                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  CONNECTION POOLING:                                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PgBouncer                                                         │   │
│  │  • Transaction mode for short queries                            │   │
│  │  • Session mode for long transactions                            │   │
│  │  • Pool size: 100 connections per service                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 10.3 Geographic Distribution

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      GLOBAL DEPLOYMENT                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐│  │
│  │    │  US-EAST-1  │         │  EU-WEST-1  │         │  AP-SOUTH-1 ││  │
│  │    │  (Primary)  │         │  (Secondary)│         │  (Tertiary) ││  │
│  │    └──────┬──────┘         └──────┬──────┘         └──────┬──────┘│  │
│  │           │                       │                       │        │  │
│  │           ▼                       ▼                       ▼        │  │
│  │    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐│  │
│  │    │ Full Stack │         │ Read Replica│         │ Read Replica││  │
│  │    │ + Primary  │         │ + CDN Edge │         │ + CDN Edge  ││  │
│  │    │ + AI GPU   │         │ + AI Cache │         │ + AI Cache  ││  │
│  │    └─────────────┘         └─────────────┘         └─────────────┘│  │
│  │                                                                    │  │
│  │  Data Replication:                                                 │  │
│  │  • Async replication from US-EAST to EU-WEST, AP-SOUTH           │  │
│  │  • RPO: 5 minutes | RTO: 15 minutes                              │  │
│  │  • DNS failover via Route 53 health checks                       │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  CDN EDGE LOCATIONS:                                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Static assets cached globally                                  │   │
│  │  • Product images cached at edge                                 │   │
│  │  • API responses cached for public endpoints                     │   │
│  │  • Edge compute for A/B testing                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 11. CI/CD Pipeline

## 11.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CI/CD PIPELINE                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    SOURCE CONTROL (GitHub)                          │  │
│  │  • Main branch (production)                                       │  │
│  │  • Develop branch (staging)                                       │  │
│  │  • Feature branches (PR-based)                                    │  │
│  │  • Protected branches with required reviews                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    CI STAGE (GitHub Actions)                        │  │
│  │                                                                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │  Lint    │→ │  Build   │→ │  Test    │→ │ Security │        │  │
│  │  │  Check   │  │          │  │  Suite   │  │  Scan    │        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  │       │             │             │             │                 │  │
│  │       ▼             ▼             ▼             ▼                 │  │
│  │   ESLint       TypeScript      Jest +       Snyk +              │  │
│  │   Prettier     Vite Build      Pytest       Trivy               │  │
│  │   Black        FastAPI         Coverage     OWASP               │  │
│  │   isort                       Report       Dependency          │  │
│  │                                                          Check    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    CD STAGE (GitHub Actions + ArgoCD)               │  │
│  │                                                                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │  Docker  │→ │  Push to │→ │  Update  │→ │  Deploy  │        │  │
│  │  │  Build   │  │  ECR     │  │  Helm    │  │  (ArgoCD)│        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  │       │             │             │             │                 │  │
│  │       ▼             ▼             ▼             ▼                 │  │
│  │   Multi-stage   AWS ECR       Kubernetes    GitOps              │  │
│  │   Build         Tagged        Helm Charts  Auto-sync            │  │
│  │   Cache layers  Images        Versioning   Rollback             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 11.2 Environment Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT ENVIRONMENTS                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  DEVELOPMENT (dev.conf.it)                                         │  │
│  │  • Auto-deploy from develop branch                                │  │
│  │  • Shared database (dev cluster)                                  │  │
│  │  • Feature flags enabled for testing                              │  │
│  │  • No GPU instances (CPU fallback)                                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  STAGING (staging.conf.it)                                         │  │
│  │  • Auto-deploy from release branches                              │  │
│  │  • Production-like configuration                                  │  │
│  │  • Reduced GPU instances (2)                                      │  │
│  │  • Full integration testing                                       │  │
│  │  • Load testing environment                                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  PRODUCTION (conf.it)                                              │  │
│  │  • Manual approval required                                       │  │
│  │  • Blue-green deployment                                          │  │
│  │  • Full GPU cluster                                               │  │
│  │  • Multi-region deployment                                        │  │
│  │  • Automated rollback on failure                                  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  DEPLOYMENT FLOW:                                                       │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│  │  Code   │───▶│  Dev    │───▶│ Staging │───▶│  Prod   │               │
│  │  Merge  │    │ Deploy  │    │ Deploy  │    │ Deploy  │               │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘               │
│       │              │              │              │                    │
│       ▼              ▼              ▼              ▼                    │
│   PR Approved    Auto (5 min)   Auto (10 min)  Manual + Approval       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 11.3 Quality Gates

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      QUALITY GATES                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  GATE 1: CODE QUALITY                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Linting: 0 errors (warnings allowed)                          │   │
│  │  • Type checking: 0 TypeScript/mypy errors                       │   │
│  │  • Code coverage: > 80% for new code                             │   │
│  │  • Complexity: Cyclomatic complexity < 15                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  GATE 2: SECURITY                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • No critical/high vulnerabilities                              │   │
│  │  • No secrets in code (gitleaks)                                  │   │
│  │  • Dependency vulnerabilities: 0 critical                        │   │
│  │  • SAST scan passed                                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  GATE 3: TESTING                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Unit tests: 100% pass                                          │   │
│  │  • Integration tests: 100% pass                                   │   │
│  │  • E2E tests: 95% pass (flaky tests allowed)                     │   │
│  │  • Performance tests: Response time < 500ms (p95)                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  GATE 4: DEPLOYMENT                                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Health checks passing                                          │   │
│  │  • No error spike in first 5 minutes                             │   │
│  │  • Response time within 10% of baseline                          │   │
│  │  • Database migration successful                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 12. Observability

## 12.1 Observability Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    LOGGING (ELK Stack / Loki)                       │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │ Fluentd/ │→ │  Log     │→ │  Elastic │→ │ Kibana/  │        │  │
│  │  │ FluentBit│  │  Agg     │  │  Search  │  │ Grafana  │        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  │  • Structured JSON logs                                           │  │
│  │  • Correlation IDs for tracing                                    │  │
│  │  • Log levels: DEBUG, INFO, WARN, ERROR                          │  │
│  │  • Retention: 30 days                                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    METRICS (Prometheus + Grafana)                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │ Exporters│→ │Prometheus│→ │  Alert   │→ │ Grafana  │        │  │
│  │  │          │  │   TSDB   │  │ Manager  │  │ Dashboards│        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  │  • System metrics (CPU, memory, disk, network)                   │  │
│  │  • Application metrics (requests, latency, errors)               │  │
│  │  • Business metrics (orders, conversions, revenue)               │  │
│  │  • AI metrics (inference time, queue depth, GPU util)            │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    TRACING (Jaeger / AWS X-Ray)                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │  OTEL    │→ │  Trace   │→ │  Jaeger  │→ │  Trace   │        │  │
│  │  │  SDK     │  │  Export  │  │ Backend  │  │  Analysis│        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  │  • Distributed tracing across services                            │  │
│  │  • Span-level latency breakdown                                   │  │
│  │  • Error attribution                                              │  │
│  │  • Service dependency mapping                                     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 12.2 Key Metrics

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      KEY METRICS (SLIs/SLOs)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SERVICE LEVEL INDICATORS (SLIs):                                       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                                                                    │   │
│  │  AVAILABILITY:                                                    │   │
│  │  • API Uptime: 99.9% SLO                                          │   │
│  │  • AI Services: 99.5% SLO                                         │   │
│  │  • Database: 99.99% SLO                                           │   │
│  │                                                                    │   │
│  │  LATENCY:                                                          │   │
│  │  • API Response (p50): < 100ms                                    │   │
│  │  • API Response (p95): < 500ms                                    │   │
│  │  • API Response (p99): < 1000ms                                   │   │
│  │  • AI Inference (p95): < 5s                                       │   │
│  │                                                                    │   │
│  │  THROUGHPUT:                                                       │   │
│  │  • Requests/sec: 1000 (baseline)                                  │   │
│  │  • Orders/min: 100 (peak capacity)                                │   │
│  │  • AI requests/min: 50 (GPU limited)                              │   │
│  │                                                                    │   │
│  │  ERRORS:                                                           │   │
│  │  • Error rate: < 0.1%                                              │   │
│  │  • 5xx errors: < 0.01%                                            │   │
│  │  • AI failures: < 1% (with fallback)                              │   │
│  │                                                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  BUSINESS METRICS:                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Daily Active Users (DAU)                                       │   │
│  │  • Conversion Rate (browse → purchase)                            │   │
│  │  • Try-On Engagement Rate                                         │   │
│  │  • Average Order Value (AOV)                                      │   │
│  │  • Customer Lifetime Value (CLV)                                  │   │
│  │  • Churn Rate                                                     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 12.3 Alerting Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ALERTING RULES                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CRITICAL (P1) - Immediate Response:                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Service down (health check failing)                            │   │
│  │  • Error rate > 5% for 2 minutes                                  │   │
│  │  • Database connection pool exhausted                            │   │
│  │  • Payment processing failures                                    │   │
│  │  Response: Page on-call, 5 min SLA                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  HIGH (P2) - Response within 30 min:                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Latency p95 > 1s for 5 minutes                                 │   │
│  │  • GPU utilization > 95%                                          │   │
│  │  • AI queue depth > 50                                            │   │
│  │  • Disk usage > 85%                                               │   │
│  │  Response: Slack alert, 30 min SLA                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  MEDIUM (P3) - Response within 4 hours:                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Memory usage > 80%                                             │   │
│  │  • SSL certificate expiring in 7 days                            │   │
│  │  • Backup failures                                                │   │
│  │  • Non-critical service degradation                              │   │
│  │  Response: Ticket creation, 4 hour SLA                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  LOW (P4) - Next business day:                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  • Slow queries detected                                          │   │
│  │  • Cache hit rate < 80%                                           │   │
│  │  • Deprecated API usage                                           │   │
│  │  Response: Weekly report aggregation                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 13. Folder Structure

## 13.1 Backend Structure

```
backend/
├── main.py                     # FastAPI application entry point
├── core/
│   ├── __init__.py
│   ├── config.py               # Settings and environment config
│   ├── security.py             # JWT, password hashing
│   └── logging.py              # Logging configuration
│
├── database/
│   ├── __init__.py
│   ├── session.py              # Database session management
│   ├── models.py               # SQLAlchemy ORM models
│   ├── migrations/             # Alembic migrations
│   │   ├── versions/
│   │   └── env.py
│   └── seed.py                 # Initial data seeding
│
├── routers/
│   ├── __init__.py
│   ├── auth.py                 # Authentication endpoints
│   ├── users.py                # User management
│   ├── products.py             # Product catalog
│   ├── orders.py               # Order management
│   ├── wardrobe.py             # Virtual wardrobe
│   ├── stylist.py              # Virtual stylist
│   ├── try_on.py               # Virtual try-on
│   ├── search.py               # Search endpoints
│   ├── payments.py             # Payment processing
│   ├── brand.py                # Brand dashboard
│   └── admin.py                # Admin endpoints
│
├── services/
│   ├── __init__.py
│   ├── auth_service.py         # Auth business logic
│   ├── user_service.py         # User operations
│   ├── product_service.py      # Product operations
│   ├── order_service.py        # Order processing
│   ├── wardrobe_service.py     # Wardrobe management
│   ├── stylist_service.py      # AI stylist logic
│   ├── try_on_service.py       # Try-on orchestration
│   ├── search_service.py       # Search operations
│   ├── payment_service.py      # Stripe integration
│   └── notification_service.py # Email/push/SMS
│
├── ai/
│   ├── __init__.py
│   ├── try_on/
│   │   ├── __init__.py
│   │   ├── pose_estimation.py  # MediaPipe pose
│   │   ├── garment_overlay.py  # OpenCV processing
│   │   └── image_synthesis.py  # Diffusion model
│   ├── stylist/
│   │   ├── __init__.py
│   │   ├── style_analyzer.py   # Style embedding
│   │   ├── context_builder.py  # RAG context
│   │   └── llm_client.py       # Groq/OpenAI client
│   ├── visual_search/
│   │   ├── __init__.py
│   │   ├── clip_encoder.py     # CLIP embeddings
│   │   └── vector_search.py    # Milvus queries
│   └── outfit_builder/
│       ├── __init__.py
│       ├── compatibility.py    # Outfit scoring
│       └── ranking.py          # Result ranking
│
├── schemas/
│   ├── __init__.py
│   ├── user.py                 # User Pydantic models
│   ├── product.py              # Product schemas
│   ├── order.py                # Order schemas
│   ├── wardrobe.py             # Wardrobe schemas
│   ├── stylist.py              # Stylist request/response
│   └── common.py               # Shared schemas
│
├── middleware/
│   ├── __init__.py
│   ├── rate_limit.py           # Rate limiting
│   ├── auth.py                 # Auth middleware
│   └── logging.py              # Request logging
│
├── utils/
│   ├── __init__.py
│   ├── cache.py                # Redis utilities
│   ├── storage.py              # S3 operations
│   └── validators.py           # Custom validators
│
├── workers/
│   ├── __init__.py
│   ├── celery_app.py           # Celery configuration
│   ├── image_tasks.py          # Image processing
│   ├── notification_tasks.py   # Async notifications
│   └── analytics_tasks.py      # Analytics aggregation
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures
    ├── test_auth.py
    ├── test_products.py
    ├── test_orders.py
    └── test_ai/
        ├── test_try_on.py
        └── test_stylist.py
```

## 13.2 Frontend Structure

```
src/
├── main.tsx                    # Application entry point
├── App.tsx                     # Root component with routing
├── vite-env.d.ts               # Vite type definitions
│
├── components/
│   ├── ui/                     # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── input.tsx
│   │   └── ...
│   │
│   ├── layout/
│   │   ├── Header.tsx          # Navigation header
│   │   ├── Footer.tsx          # Site footer
│   │   ├── Sidebar.tsx         # Dashboard sidebar
│   │   └── MobileNav.tsx       # Mobile navigation
│   │
│   ├── products/
│   │   ├── ProductCard.tsx     # Product display card
│   │   ├── ProductGrid.tsx     # Product listing
│   │   ├── ProductDetail.tsx   # Product page
│   │   └── ProductFilters.tsx  # Filter sidebar
│   │
│   ├── wardrobe/
│   │   ├── WardrobeGrid.tsx    # Wardrobe display
│   │   ├── WardrobeItem.tsx    # Single item card
│   │   ├── AddItemModal.tsx    # Add item dialog
│   │   └── TagEditor.tsx       # Tag management
│   │
│   ├── stylist/
│   │   ├── ChatInterface.tsx   # Stylist chat UI
│   │   ├── RecommendationCard.tsx
│   │   └── StyleQuiz.tsx       # Style preference quiz
│   │
│   ├── try-on/
│   │   ├── TryOnViewer.tsx     # Try-on result viewer
│   │   ├── PhotoUploader.tsx   # Photo upload
│   │   └── GarmentSelector.tsx # Garment selection
│   │
│   ├── checkout/
│   │   ├── Cart.tsx            # Shopping cart
│   │   ├── CheckoutForm.tsx    # Checkout flow
│   │   └── PaymentStatus.tsx   # Payment result
│   │
│   └── brand/
│       ├── BrandDashboard.tsx  # Brand overview
│       ├── AnalyticsCharts.tsx # Performance charts
│       └── InventoryTable.tsx  # Inventory management
│
├── pages/
│   ├── Home.tsx                # Landing page
│   ├── Login.tsx               # Login page
│   ├── Register.tsx            # Registration
│   ├── Products.tsx            # Product catalog
│   ├── ProductDetail.tsx       # Single product
│   ├── Wardrobe.tsx            # Virtual wardrobe
│   ├── Stylist.tsx             # Virtual stylist
│   ├── TryOn.tsx               # Virtual try-on
│   ├── VisualSearch.tsx        # Visual search
│   ├── Outfits.tsx             # Outfit builder
│   ├── Checkout.tsx            # Checkout page
│   ├── Orders.tsx              # Order history
│   ├── Profile.tsx             # User profile
│   ├── BrandDashboard.tsx      # Brand portal
│   ├── DigitalTwin.tsx         # 3D body model
│   ├── Resale.tsx              # Resale marketplace
│   ├── SmartMirror.tsx         # Smart mirror UI
│   ├── Challenges.tsx          # Gamification
│   ├── Analytics.tsx           # User analytics
│   └── NotFound.tsx            # 404 page
│
├── context/
│   ├── AuthContext.tsx         # Authentication state
│   ├── CartContext.tsx         # Shopping cart state
│   ├── WishlistContext.tsx     # Wishlist state
│   ├── GenderContext.tsx       # Gender preference
│   └── ThemeContext.tsx        # Theme (light/dark)
│
├── hooks/
│   ├── useAuth.ts              # Auth hook
│   ├── useCart.ts              # Cart operations
│   ├── useProducts.ts          # Product fetching
│   ├── useWardrobe.ts          # Wardrobe operations
│   ├── useStylist.ts           # Stylist chat
│   ├── useTryOn.ts             # Try-on operations
│   ├── useDebounce.ts          # Debounce utility
│   └── useLocalStorage.ts      # Local storage
│
├── services/
│   ├── api.ts                  # Axios instance
│   ├── authService.ts          # Auth API calls
│   ├── productService.ts       # Product API
│   ├── orderService.ts         # Order API
│   ├── wardrobeService.ts      # Wardrobe API
│   ├── stylistService.ts       # Stylist API
│   ├── tryOnService.ts         # Try-on API
│   └── paymentService.ts       # Payment API
│
├── lib/
│   ├── utils.ts                # Utility functions
│   ├── constants.ts            # App constants
│   └── validators.ts           # Form validation
│
├── types/
│   ├── user.ts                 # User types
│   ├── product.ts              # Product types
│   ├── order.ts                # Order types
│   ├── wardrobe.ts             # Wardrobe types
│   └── api.ts                  # API response types
│
├── styles/
│   ├── globals.css             # Global styles
│   └── themes/                 # Theme variants
│
└── assets/
    ├── images/                 # Static images
    ├── icons/                  # Icon files
    └── fonts/                  # Custom fonts
```

## 13.3 Infrastructure Structure

```
infrastructure/
├── docker/
│   ├── Dockerfile.api          # API service image
│   ├── Dockerfile.ai           # AI service image (GPU)
│   ├── Dockerfile.worker       # Celery worker image
│   ├── Dockerfile.frontend     # Frontend build image
│   └── docker-compose.yml      # Local development
│
├── kubernetes/
│   ├── base/
│   │   ├── deployment-api.yaml
│   │   ├── deployment-ai.yaml
│   │   ├── deployment-worker.yaml
│   │   ├── service-api.yaml
│   │   ├── service-ai.yaml
│   │   ├── configmap.yaml
│   │   └── secrets.yaml
│   │
│   ├── overlays/
│   │   ├── dev/
│   │   │   └── kustomization.yaml
│   │   ├── staging/
│   │   │   └── kustomization.yaml
│   │   └── production/
│   │       └── kustomization.yaml
│   │
│   └── helm/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-dev.yaml
│       ├── values-staging.yaml
│       └── values-production.yaml
│
├── terraform/
│   ├── modules/
│   │   ├── vpc/                # VPC configuration
│   │   ├── eks/                # Kubernetes cluster
│   │   ├── rds/                # PostgreSQL
│   │   ├── elasticache/        # Redis
│   │   ├── s3/                 # Storage buckets
│   │   └── cloudfront/         # CDN
│   │
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── main.tf
│   │   │   └── variables.tf
│   │   ├── staging/
│   │   │   ├── main.tf
│   │   │   └── variables.tf
│   │   └── production/
│   │       ├── main.tf
│   │       └── variables.tf
│   │
│   └── global/
│       ├── iam.tf              # IAM roles
│       └── route53.tf          # DNS
│
├── ansible/
│   ├── playbooks/
│   │   ├── setup-server.yaml
│   │   └── deploy.yaml
│   └── inventory/
│       ├── dev.ini
│       └── production.ini
│
└── scripts/
    ├── deploy.sh               # Deployment script
    ├── rollback.sh             # Rollback script
    ├── backup.sh               # Database backup
    └── seed-data.sh            # Data seeding
```

---

# 14. Deployment Diagram

## 14.1 Production Deployment

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PRODUCTION DEPLOYMENT                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    AWS CLOUD (US-EAST-1)                          │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  ROUTE 53 (DNS)                                              │  │  │
│  │  │  • conf.it → CloudFront                                      │  │  │
│  │  │  • api.conf.it → ALB                                         │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                           │                                        │  │
│  │                           ▼                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  CLOUDFRONT (CDN)                                            │  │  │
│  │  │  • Static assets (S3 origin)                                 │  │  │
│  │  │  • API caching                                               │  │  │
│  │  │  • WAF rules                                                 │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                           │                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  VPC (10.0.0.0/16)                                           │  │  │
│  │  │                                                               │  │  │
│  │  │  ┌───────────────────────────────────────────────────────┐   │  │  │
│  │  │  │  PUBLIC SUBNETS (AZ-a, AZ-b)                           │   │  │  │
│  │  │  │  ┌─────────────────┐  ┌─────────────────┐             │   │  │  │
│  │  │  │  │  ALB (Public)   │  │  NAT Gateway    │             │   │  │  │
│  │  │  │  │  Port 443       │  │  (Outbound)     │             │   │  │  │
│  │  │  │  └────────┬────────┘  └─────────────────┘             │   │  │  │
│  │  │  └───────────┼────────────────────────────────────────────┘   │  │  │
│  │  │              │                                                    │  │  │
│  │  │  ┌───────────┼────────────────────────────────────────────┐    │  │  │
│  │  │  │           ▼        PRIVATE SUBNETS                      │    │  │  │
│  │  │  │  ┌─────────────────────────────────────────────────┐   │    │  │  │
│  │  │  │  │  EKS CLUSTER (Kubernetes)                        │   │    │  │  │
│  │  │  │  │                                                  │   │    │  │  │
│  │  │  │  │  ┌─────────────┐  ┌─────────────┐              │   │    │  │  │
│  │  │  │  │  │ API Pods    │  │ AI Pods     │              │   │    │  │  │
│  │  │  │  │  │ (m6i.xlarge)│  │ (g5.xlarge) │              │   │    │  │  │
│  │  │  │  │  │ Replicas: 4 │  │ Replicas: 2 │              │   │    │  │  │
│  │  │  │  │  └─────────────┘  └─────────────┘              │   │    │  │  │
│  │  │  │  │                                                  │   │    │  │  │
│  │  │  │  │  ┌─────────────┐  ┌─────────────┐              │   │    │  │  │
│  │  │  │  │  │ Workers     │  │ Scheduler   │              │   │    │  │  │
│  │  │  │  │  │ (m6i.2xlarge)│  │ (m6i.large) │              │   │    │  │  │
│  │  │  │  │  │ Replicas: 4 │  │ Replicas: 1 │              │   │    │  │  │
│  │  │  │  │  └─────────────┘  └─────────────┘              │   │    │  │  │
│  │  │  │  └──────────────────────────────────────────────────┘   │    │  │  │
│  │  │  └─────────────────────────────────────────────────────────┘    │  │  │
│  │  │                          │                                       │  │  │
│  │  │  ┌───────────────────────┼─────────────────────────────────┐    │  │  │
│  │  │  │                       ▼         DATA SUBNETS            │    │  │  │
│  │  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │    │  │  │
│  │  │  │  │  RDS        │  │ ElastiCache │  │  S3         │     │    │  │  │
│  │  │  │  │  PostgreSQL │  │  Redis      │  │  Storage    │     │    │  │  │
│  │  │  │  │  Multi-AZ   │  │  Cluster    │  │  Buckets    │     │    │  │  │
│  │  │  │  │  r6g.xlarge │  │  r6g.large  │  │             │     │    │  │  │
│  │  │  │  └─────────────┘  └─────────────┘  └─────────────┘     │    │  │  │
│  │  │  │                                                        │    │  │  │
│  │  │  │  ┌─────────────┐  ┌─────────────┐                     │    │  │  │
│  │  │  │  │ OpenSearch  │  │  Milvus     │                     │    │  │  │
│  │  │  │  │  (Search)   │  │  (Vector)   │                     │    │  │  │
│  │  │  │  │  3 nodes    │  │  2 nodes    │                     │    │  │  │
│  │  │  │  └─────────────┘  └─────────────┘                     │    │  │  │
│  │  │  └────────────────────────────────────────────────────────┘    │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  MANAGED SERVICES                                            │  │  │
│  │  │  • AWS Cognito (OAuth)                                       │  │  │
│  │  │  • AWS Secrets Manager                                       │  │  │
│  │  │  • AWS KMS (Encryption)                                      │  │  │
│  │  │  • AWS SES (Email)                                           │  │  │
│  │  │  • Stripe (Payments)                                         │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 14.2 Kubernetes Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      KUBERNETES CLUSTER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  NAMESPACE: CONFIT-APP                                            │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  DEPLOYMENTS                                                 │  │  │
│  │  │                                                               │  │  │
│  │  │  api-deployment                                               │  │  │
│  │  │  ├── Replicas: 4                                              │  │  │
│  │  │  ├── Image: confit-api:v1.2.3                                │  │  │
│  │  │  ├── Resources: 1 CPU, 2GB RAM                               │  │  │
│  │  │  └── Probes: Liveness, Readiness                             │  │  │
│  │  │                                                               │  │  │
│  │  │  ai-deployment                                                │  │  │
│  │  │  ├── Replicas: 2                                              │  │  │
│  │  │  ├── Image: confit-ai:v1.2.3                                 │  │  │
│  │  │  ├── Resources: 4 CPU, 16GB RAM, 1 GPU                       │  │  │
│  │  │  └── Node Selector: gpu=true                                 │  │  │
│  │  │                                                               │  │  │
│  │  │  worker-deployment                                            │  │  │
│  │  │  ├── Replicas: 4                                              │  │  │
│  │  │  ├── Image: confit-worker:v1.2.3                              │  │  │
│  │  │  └── Resources: 2 CPU, 4GB RAM                                │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  SERVICES                                                    │  │  │
│  │  │  ├── api-service (ClusterIP)                                 │  │  │
│  │  │  ├── ai-service (ClusterIP)                                  │  │  │
│  │  │  └── api-headless (for StatefulSet)                          │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  HORIZONTAL POD AUTOSCALERS                                  │  │  │
│  │  │  ├── api-hpa (2-20 pods, CPU 70%)                            │  │  │
│  │  │  └── worker-hpa (2-50 pods, Queue depth)                     │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  CONFIGMAPS & SECRETS                                        │  │  │
│  │  │  ├── app-config (non-sensitive config)                        │  │  │
│  │  │  ├── db-credentials (Secret)                                 │  │  │
│  │  │  ├── api-keys (Secret)                                       │  │  │
│  │  │  └── tls-certs (Secret)                                      │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  NAMESPACE: MONITORING                                            │  │
│  │  ├── Prometheus (metrics collection)                             │  │
│  │  ├── Grafana (dashboards)                                        │  │
│  │  ├── Alertmanager (alert routing)                                │  │
│  │  └── Loki (log aggregation)                                      │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  NAMESPACE: ARGOCD                                                │  │
│  │  └── GitOps deployment management                                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 15. Tech Stack Reasoning

## 15.1 Backend Technologies

| Technology | Rationale |
|------------|-----------|
| **FastAPI** | Async-first Python framework with automatic OpenAPI docs, Pydantic validation, and high performance. Ideal for AI-heavy workloads with Python ecosystem. |
| **PostgreSQL** | ACID-compliant relational database with JSON support, full-text search, and excellent scalability via Citus. Industry standard for e-commerce. |
| **Redis** | In-memory cache for sessions, rate limiting, and real-time features. Pub/Sub for event-driven architecture. |
| **SQLAlchemy** | Mature ORM with async support, connection pooling, and migration support via Alembic. |
| **Celery** | Battle-tested distributed task queue for background jobs, image processing, and AI inference queuing. |
| **Pydantic** | Type-safe data validation with automatic schema generation. Integrates seamlessly with FastAPI. |

## 15.2 Frontend Technologies

| Technology | Rationale |
|------------|-----------|
| **React 18** | Component-based architecture with concurrent features, Suspense, and large ecosystem. Industry standard for SPAs. |
| **Vite** | Fast development server with HMR, optimized production builds, and native ESM support. |
| **TypeScript** | Type safety, better IDE support, and reduced runtime errors. Essential for large codebases. |
| **Tailwind CSS** | Utility-first CSS for rapid UI development with consistent design system. |
| **shadcn/ui** | Accessible, customizable component library built on Radix UI primitives. |
| **React Router** | Declarative routing with nested routes and lazy loading support. |

## 15.3 AI/ML Technologies

| Technology | Rationale |
|------------|-----------|
| **Stable Diffusion + ControlNet** | State-of-the-art image synthesis for virtual try-on with pose control. Open-source, customizable. |
| **Llama 3 (via Groq)** | Fast inference for stylist chat at 500+ tokens/sec. Cost-effective compared to GPT-4. |
| **CLIP (ViT-L/14)** | Vision-language model for visual search and product embeddings. Proven accuracy. |
| **MediaPipe** | Real-time pose estimation for try-on alignment. Runs on CPU, no GPU required. |
| **Milvus** | Open-source vector database for similarity search. Scales to billions of vectors. |
| **OpenCV** | Image processing for preprocessing, background removal, and geometric transforms. |

## 15.4 Infrastructure Technologies

| Technology | Rationale |
|------------|-----------|
| **Kubernetes (EKS)** | Container orchestration with auto-scaling, self-healing, and declarative configuration. |
| **Docker** | Containerization for consistent environments across dev, staging, and production. |
| **Terraform** | Infrastructure as Code for reproducible, version-controlled infrastructure. |
| **ArgoCD** | GitOps deployment tool with automatic sync, rollback, and audit trail. |
| **GitHub Actions** | Native CI/CD with matrix builds, caching, and extensive marketplace. |
| **AWS Cloud** | Comprehensive managed services, global regions, and enterprise compliance certifications. |

## 15.5 Observability Technologies

| Technology | Rationale |
|------------|-----------|
| **Prometheus** | Time-series metrics database with powerful query language (PromQL). CNCF standard. |
| **Grafana** | Unified visualization for metrics, logs, and traces. Rich alerting ecosystem. |
| **Jaeger** | Distributed tracing with OpenTelemetry support. Visualizes service dependencies. |
| **Loki** | Log aggregation designed for Prometheus ecosystem. Cost-effective log storage. |
| **OpenTelemetry** | Vendor-neutral telemetry standard. Future-proof instrumentation. |

---

# 16. Data Flow Summary

## 16.1 Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      REQUEST LIFECYCLE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. CLIENT REQUEST                                                      │
│     └── User action → HTTP request → CDN edge                          │
│                                                                          │
│  2. EDGE PROCESSING                                                     │
│     └── CDN cache check → TLS termination → WAF rules                  │
│                                                                          │
│  3. API GATEWAY                                                         │
│     └── Rate limiting → JWT validation → Request routing               │
│                                                                          │
│  4. SERVICE LAYER                                                       │
│     └── Business logic → Cache check → Database query                  │
│                                                                          │
│  5. RESPONSE                                                            │
│     └── Cache population → Response transformation → Client delivery   │
│                                                                          │
│  6. ASYNC PROCESSING (if applicable)                                    │
│     └── Event emission → Queue processing → Side effects               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 16.2 Key Data Flows

### User Registration
```
Client → API Gateway → Auth Service → User Service → PostgreSQL
                                    → Redis (session) → Email Worker
```

### Virtual Try-On
```
Client → API Gateway → Try-On Service → S3 (upload)
                                    → AI Queue → GPU Worker → S3 (result)
                                    → WebSocket notification → Client
```

### Product Purchase
```
Client → API Gateway → Order Service → PostgreSQL (order)
                                    → Inventory Service → PostgreSQL (inventory)
                                    → Payment Service → Stripe API
                                    → Notification Worker → Email/SMS
                                    → Analytics Worker → Events DB
```

### Virtual Stylist Chat
```
Client → API Gateway → Stylist Service → Redis (cache check)
                                       → LLM Client → Groq API
                                       → Product Service → Recommendations
                                       → WebSocket → Client (streaming)
```

---

# 17. Glossary

| Term | Definition |
|------|------------|
| **Bounded Context** | A DDD pattern where each domain has its own model, database, and business logic boundaries. |
| **CQRS** | Command Query Responsibility Segregation - separating read and write operations for scalability. |
| **Event Sourcing** | Storing state changes as a sequence of events rather than current state. |
| **Saga** | A sequence of local transactions for distributed transactions across services. |
| **Circuit Breaker** | A pattern that prevents cascading failures by stopping calls to failing services. |
| **Backpressure** | A mechanism to handle load by controlling the rate of incoming requests. |
| **SLA/SLO/SLI** | Service Level Agreement/Objective/Indicator - reliability metrics and targets. |
| **GitOps** | Infrastructure and deployment management using Git as the source of truth. |
| **Blue-Green Deployment** | A deployment strategy with two identical environments for zero-downtime releases. |
| **Feature Flag** | A toggle that enables/disables features without code deployment. |

---

# 18. Appendix

## 18.1 Environment Variables

```bash
# Core Configuration
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql://user:pass@host:5432/confit

# Security
JWT_SECRET=your-256-bit-secret-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# CORS
FRONTEND_URL=https://conf.it
ALLOWED_ORIGINS=https://conf.it,https://www.conf.it

# External APIs
HF_TOKEN=hf_xxxxx
GROQ_API_KEY=gsk_xxxxx
OPENAI_API_KEY=sk_xxxxx
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Feature Flags
ENABLE_RATE_LIMITING=true
ENABLE_AI_FEATURES=true
ENABLE_TRY_ON=true

# Rate Limits
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_TRY_ON=10/minute

# Storage
AWS_ACCESS_KEY_ID=AKIAxxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
S3_BUCKET_PRODUCTS=confit-products
S3_BUCKET_TRY_ON=confit-try-on-results

# Redis
REDIS_URL=redis://host:6379/0

# Search
ELASTICSEARCH_URL=https://es.conf.it:9200
MILVUS_HOST=milvus.conf.it

# Monitoring
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.conf.it:4317
```

## 18.2 Health Check Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/health` | Load balancer health check | `{"status": "healthy"}` |
| `/health/ready` | Readiness probe (dependencies) | `{"status": "ready", "checks": {...}}` |
| `/health/live` | Liveness probe (deadlock detection) | `{"status": "alive"}` |

## 18.3 API Versioning Strategy

- **URL Path Versioning**: `/api/v1/`, `/api/v2/`
- **Backward Compatibility**: New fields are additive, removal requires version bump
- **Deprecation Policy**: 6-month sunset period with `Deprecation` header
- **Version Support**: N and N-1 versions supported simultaneously

---

*Document Version: 1.0.0*
*Last Updated: 2025*
*Authors: CONFIT Architecture Team*