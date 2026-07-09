export type Language = 'en' | 'ru'

// Intl locale per UI language — number grouping and date order follow the
// language switch so «1 234,56 · 14.01.2025» becomes "1,234.56 · 01/14/2025".
export const LOCALES: Record<Language, string> = { en: 'en-US', ru: 'ru-RU' }

const en = {
  // Sidebar
  localBadge: 'local',
  newChat: 'New chat',
  needsCategory: 'Needs category',
  documents: 'Documents',
  uploadStatement: 'Upload statement',
  chats: 'Chats',
  rename: 'Rename',
  delete: 'Delete',
  fileNotParsed: 'File not parsed yet',
  llmChecking: 'Checking…',
  openaiConnected: 'OpenAI connected',
  ollamaLocal: 'Ollama (local)',
  deleteChatTitle: 'Delete chat?',
  deleteChatMessage: 'The chat “{name}” and its history will be deleted permanently.',
  deleteFileTitle: 'Delete file?',
  deleteFileMessage: 'The file “{name}” and all its transactions will be deleted permanently.',

  // ConfirmDialog
  cancel: 'Cancel',

  // EmptyState
  emptyTitle: 'What do you want to ask your statements?',
  emptySubtitle:
    'Upload a bank statement — PDF or CSV — and ask questions in plain language. ' +
    'Everything runs on your own machine.',
  dropStatementHere: 'Drop a statement here',
  orClickToChoose: 'or click to choose a file · PDF, CSV',
  processedLocally: 'everything is processed locally, nothing leaves your machine',
  starter1: 'What am I spending the most on?',
  starter2: 'Compare March and February',
  starter3: 'Find subscriptions',
  starter4: 'Large one-off expenses',

  // Composer
  composerPlaceholder: 'Ask about your spending…',
  composerHint: 'Enter — send · Shift+Enter — new line',

  // AtPicker
  atPlaceholder: 'file or folder…',
  nothingFound: 'Nothing found',
  filesCount: '{n} files',
  txCount: '{n} transactions',
  notParsed: 'not parsed',

  // ChatFeed
  toolsLabel: 'Tools',
  scopeAuto: 'Scope chosen by the agent:',
  scopeManual: 'Selected scope:',
  agentThinking: 'FinAgent is analyzing',

  // Blocks
  chartLoading: 'Loading chart…',
  donutTotal: 'total',

  // DocumentViewer
  backToChat: 'Back to chat',
  statusParsed: 'Parsed',
  statusParsing: 'Processing',
  statusNew: 'New',
  statusError: 'Error',
  period: 'Period',
  colDate: 'Date',
  colMerchant: 'Merchant',
  colCategory: 'Category',
  colAmount: 'Amount',
  loading: 'Loading…',
  totalTransactions: 'Total transactions: {n}',

  // CategoryReviewPanel
  newCategory: 'New category',
  allCategorized: 'All merchants are categorized',
  chooseCategory: 'Choose a category',
  newCategoryOption: '+ New category…',
  categoryName: 'Name',
  categoryNamePlaceholder: 'e.g. “Subscriptions”',
  categoryColor: 'Color',
  create: 'Create',

  // SettingsModal
  settings: 'Settings',
  llmProvider: 'LLM provider',
  llmProviderNote:
    'The provider is configured via server environment variables ' +
    '(LLM_PROVIDER, OPENAI_API_KEY / OLLAMA_HOST).',
  theme: 'Theme',
  themeLight: '☀ Light',
  themeDark: '☾ Dark',
  language: 'Language',

  // UploadModal
  uploadTitle: 'Upload a statement',
  folder: 'Folder',
  folderPlaceholder: 'e.g. 2025-01 (optional)',
  dragOrChoose: 'Drag a file here or choose one',
  pdfOrCsv: 'PDF or CSV',
  uploadNote: 'PDF (via OCR) and CSV are supported. Your data never leaves your machine.',
  uploading: 'Uploading and parsing',
  doneOpenChat: 'Done — open chat',
  megabytes: '{n} MB',
} as const

export type TranslationKey = keyof typeof en

const ru: Record<TranslationKey, string> = {
  localBadge: 'локально',
  newChat: 'Новый чат',
  needsCategory: 'Требуют категории',
  documents: 'Документы',
  uploadStatement: 'Загрузить выписку',
  chats: 'Чаты',
  rename: 'Переименовать',
  delete: 'Удалить',
  fileNotParsed: 'Файл ещё не распознан',
  llmChecking: 'Проверка…',
  openaiConnected: 'OpenAI подключён',
  ollamaLocal: 'Ollama (локально)',
  deleteChatTitle: 'Удалить чат?',
  deleteChatMessage: 'Чат «{name}» и его история будут удалены без возможности восстановления.',
  deleteFileTitle: 'Удалить файл?',
  deleteFileMessage:
    'Файл «{name}» и все его транзакции будут удалены без возможности восстановления.',

  cancel: 'Отмена',

  emptyTitle: 'О чём спросить свои выписки?',
  emptySubtitle:
    'Загрузите банковскую выписку — PDF или CSV — и задайте вопрос обычным языком. ' +
    'Всё считается на вашей машине.',
  dropStatementHere: 'Перетащите выписку сюда',
  orClickToChoose: 'или нажмите, чтобы выбрать файл · PDF, CSV',
  processedLocally: 'всё обрабатывается локально, ничего не уходит наружу',
  starter1: 'На что я трачу больше всего?',
  starter2: 'Сравни март и февраль',
  starter3: 'Найди подписки',
  starter4: 'Крупные разовые траты',

  composerPlaceholder: 'Спросите про свои траты…',
  composerHint: 'Enter — отправить · Shift+Enter — перенос',

  atPlaceholder: 'файл или папка…',
  nothingFound: 'Ничего не найдено',
  filesCount: '{n} файлов',
  txCount: '{n} операций',
  notParsed: 'не распознано',

  toolsLabel: 'Инструменты',
  scopeAuto: 'Агент сам определил область:',
  scopeManual: 'Указанная область:',
  agentThinking: 'FinAgent анализирует',

  chartLoading: 'Загрузка графика…',
  donutTotal: 'всего',

  backToChat: 'В чат',
  statusParsed: 'Распарсено',
  statusParsing: 'Обрабатывается',
  statusNew: 'Новая',
  statusError: 'Ошибка',
  period: 'Период',
  colDate: 'Дата',
  colMerchant: 'Продавец',
  colCategory: 'Категория',
  colAmount: 'Сумма',
  loading: 'Загрузка…',
  totalTransactions: 'Всего транзакций: {n}',

  newCategory: 'Новая категория',
  allCategorized: 'Все продавцы категоризированы',
  chooseCategory: 'Выбрать категорию',
  newCategoryOption: '+ Новая категория…',
  categoryName: 'Название',
  categoryNamePlaceholder: 'Например, «Подписки»',
  categoryColor: 'Цвет',
  create: 'Создать',

  settings: 'Настройки',
  llmProvider: 'Провайдер LLM',
  llmProviderNote:
    'Провайдер задаётся переменными окружения на сервере ' +
    '(LLM_PROVIDER, OPENAI_API_KEY / OLLAMA_HOST).',
  theme: 'Тема',
  themeLight: '☀ Светлая',
  themeDark: '☾ Тёмная',
  language: 'Язык',

  uploadTitle: 'Загрузка выписки',
  folder: 'Папка',
  folderPlaceholder: 'например, 2025-01 (необязательно)',
  dragOrChoose: 'Перетащите файл или выберите',
  pdfOrCsv: 'PDF или CSV',
  uploadNote: 'Поддерживаются PDF (через OCR) и CSV. Данные не покидают вашу машину.',
  uploading: 'Загрузка и разбор',
  doneOpenChat: 'Готово — открыть чат',
  megabytes: '{n} МБ',
}

const translations: Record<Language, Record<TranslationKey, string>> = { en, ru }

export type TranslateParams = Record<string, string | number>

export function translate(
  language: Language,
  key: TranslationKey,
  params?: TranslateParams,
): string {
  let text: string = translations[language][key]
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.replaceAll(`{${name}}`, String(value))
    }
  }
  return text
}
