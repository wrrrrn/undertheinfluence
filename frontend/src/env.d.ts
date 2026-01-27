/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly DATA_API_URL: string;
  readonly WAGTAIL_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
