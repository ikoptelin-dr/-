// Контентная модель сайта (ТЗ, раздел 3). Схемы zod проверяются при сборке.
// Каталог контента можно подменить через PROBA_CONTENT_DIR (используется в тестах).
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const CONTENT_DIR = process.env.PROBA_CONTENT_DIR || './src/content';

const slug = z.string().regex(/^[a-z0-9-]+$/, 'slug: только латиница в нижнем регистре, цифры и дефис');

const source = z.object({
  title: z.string().min(1),
  url: z.string().url(),
  year: z.number().int().min(1800).max(2100),
  type: z.string().min(1), // обзор, РКИ, когортное, клинический случай…
  on_whom: z.enum(['люди', 'животные', 'клетки']),
});

const review = z.object({
  reviewer_name: z.string().optional(),
  reviewer_title: z.string().optional(),
  reviewed_at: z.coerce.date().optional(),
  // Расширение сайта (DECISIONS D-036): срок действия одобрения, как в review.schema.json.
  expires_at: z.coerce.date().optional(),
  version: z.number().int().min(1).optional(),
  content_sha256: z.string().regex(/^[a-f0-9]{64}$/).optional(),
  status: z.enum(['draft', 'in_review', 'approved']),
});

const materials = defineCollection({
  loader: glob({ pattern: '**/*.md', base: `${CONTENT_DIR}/materials` }),
  schema: z.object({
    title: z.string().min(1),
    slug,
    section: z.enum(['pro', 'dlya-vseh']),
    kind: z.enum(['hub', 'razbor', 'ne-akne', 'pamyatka', 'article']),
    // Расширение сайта (D-036): хаб для раздела «Для всех» (posle-procedur, pryshchi, ne-akne, procedury).
    hub: slug.optional(),
    summary: z.string().min(1).max(200),
    medical: z.boolean(),
    pro_only: z.boolean().default(false),
    review: review.optional(),
    sources: z.array(source).optional(),
    disclosure: z.string().min(1),
    sponsored: z
      .object({ sponsor: z.string(), marking_erid: z.string().optional() })
      .nullable()
      .default(null),
    updated_at: z.coerce.date(),
    changelog: z.array(z.object({ date: z.coerce.date(), change: z.string().min(1) })).default([]),
  }),
});

const webinars = defineCollection({
  loader: glob({ pattern: '**/*.md', base: `${CONTENT_DIR}/webinars` }),
  schema: z.object({
    title: z.string().min(1),
    slug,
    summary: z.string().min(1).max(200),
    audience: z.string().min(1),
    program: z.array(z.string().min(1)).min(1),
    speaker: z.object({
      name: z.string().optional(),
      title: z.string().optional(),
      consent: z.boolean().default(false),
    }),
    date: z.coerce.date().nullable().default(null),
    duration: z.string().min(1),
    price: z.string().nullable().default(null),
    payment_url: z.string().url().nullable().default(null),
    status: z.enum(['presale', 'scheduled', 'done', 'waitlist']),
    materials_after: z.array(z.string()).default([]),
  }),
});

const people = defineCollection({
  loader: glob({ pattern: '**/*.md', base: `${CONTENT_DIR}/people` }),
  schema: z.object({
    name: z.string().min(1),
    role: z.string().min(1),
    bio: z.string().default(''),
    consent_public: z.boolean().default(false),
  }),
});

// Простые страницы (о проекте, правовые). legal_draft → плашка «финальный текст — юрист».
const pages = defineCollection({
  loader: glob({ pattern: '**/*.md', base: `${CONTENT_DIR}/pages` }),
  schema: z.object({
    title: z.string().min(1),
    description: z.string().min(1).max(200),
    legal_draft: z.boolean().default(false),
    noindex: z.boolean().default(false),
    updated_at: z.coerce.date(),
  }),
});

export const collections = { materials, webinars, people, pages };
