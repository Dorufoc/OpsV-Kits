import {
  mdiRefresh,
  mdiClose,
  mdiConnection,
  mdiKey,
  mdiDelete,
  mdiFolderOpen,
  mdiContentCopy,
  mdiCheckCircle,
  mdiPlus,
  mdiCheck,
  mdiMonitor,
  mdiInformation,
  mdiCpu64Bit,
  mdiCurrencyUsd,
  mdiFolder,
  mdiLoading,
  mdiClockOutline,
  mdiPencil,
  mdiStar,
  mdiAlertCircle,
  mdiAlert,
  mdiArrowUp,
  mdiTag,
  mdiTextBox,
  mdiFolderMultiple,
  mdiAccount,
  mdiLayers,
  mdiArrowLeft,
  mdiMagnify,
  mdiUpload,
  mdiDownload,
  mdiCog,
  mdiHelpCircle,
  mdiPackageVariant,
  mdiPlay,
  mdiPause,
  mdiMinus,
  mdiChartBar,
  mdiFullscreen,
  mdiFullscreenExit,
  mdiTimerOutline,
  mdiHome,
  mdiChartLine,
  mdiAccountBox,
  mdiWrench,
} from '@mdi/js'

// 部分@mdi/js中不存在的图标，使用替代方案
const mdiCoin = mdiCurrencyUsd  // 用美元符号替代硬币图标
const mdiBox = mdiPackageVariant  // 用package替代box图标

export type IconName =
  | 'refresh'
  | 'close'
  | 'connection'
  | 'key'
  | 'delete'
  | 'folder-open'
  | 'content-copy'
  | 'check-circle'
  | 'plus'
  | 'check'
  | 'monitor'
  | 'information'
  | 'cpu'
  | 'coin'
  | 'folder'
  | 'loading'
  | 'clock'
  | 'pencil'
  | 'star'
  | 'alert-circle'
  | 'alert'
  | 'arrow-up'
  | 'tag'
  | 'text-box'
  | 'folder-multiple'
  | 'account'
  | 'collection'
  | 'arrow-left'
  | 'magnify'
  | 'upload'
  | 'download'
  | 'cog'
  | 'help-circle'
  | 'box'
  | 'play'
  | 'pause'
  | 'remove'
  | 'chart-bar'
  | 'fullscreen'
  | 'fullscreen-exit'
  | 'timer'
  | 'home'
  | 'chart-line'
  | 'account-box'
  | 'wrench'

export const iconMap: Record<string, string> = {
  'refresh': mdiRefresh,
  'close': mdiClose,
  'connection': mdiConnection,
  'key': mdiKey,
  'delete': mdiDelete,
  'folder-open': mdiFolderOpen,
  'content-copy': mdiContentCopy,
  'check-circle': mdiCheckCircle,
  'plus': mdiPlus,
  'check': mdiCheck,
  'monitor': mdiMonitor,
  'information': mdiInformation,
  'cpu': mdiCpu64Bit,
  'coin': mdiCoin,
  'folder': mdiFolder,
  'loading': mdiLoading,
  'clock': mdiClockOutline,
  'pencil': mdiPencil,
  'star': mdiStar,
  'alert-circle': mdiAlertCircle,
  'alert': mdiAlert,
  'arrow-up': mdiArrowUp,
  'tag': mdiTag,
  'text-box': mdiTextBox,
  'folder-multiple': mdiFolderMultiple,
  'account': mdiAccount,
  'collection': mdiLayers,
  'arrow-left': mdiArrowLeft,
  'magnify': mdiMagnify,
  'upload': mdiUpload,
  'download': mdiDownload,
  'cog': mdiCog,
  'help-circle': mdiHelpCircle,
  'box': mdiBox,
  'play': mdiPlay,
  'pause': mdiPause,
  'remove': mdiMinus,
  'chart-bar': mdiChartBar,
  'fullscreen': mdiFullscreen,
  'fullscreen-exit': mdiFullscreenExit,
  'timer': mdiTimerOutline,
  'home': mdiHome,
  'chart-line': mdiChartLine,
  'account-box': mdiAccountBox,
  'wrench': mdiWrench,
}

export const elementPlusToMdiMap: Record<string, IconName> = {
  'Refresh': 'refresh',
  'Close': 'close',
  'CircleClose': 'close',
  'Connection': 'connection',
  'Key': 'key',
  'Delete': 'delete',
  'FolderOpened': 'folder-open',
  'DocumentCopy': 'content-copy',
  'CopyDocument': 'content-copy',
  'SuccessFilled': 'check-circle',
  'CircleCheck': 'check-circle',
  'Plus': 'plus',
  'Check': 'check',
  'Monitor': 'monitor',
  'InfoFilled': 'information',
  'Cpu': 'cpu',
  'Coin': 'coin',
  'Folder': 'folder',
  'Loading': 'loading',
  'Clock': 'clock',
  'Edit': 'pencil',
  'StarFilled': 'star',
  'Warning': 'alert',
  'WarningFilled': 'alert-circle',
  'Top': 'arrow-up',
  'Tickets': 'tag',
  'Document': 'text-box',
  'Files': 'folder-multiple',
  'User': 'account',
  'UserFilled': 'account-box',
  'Collection': 'collection',
  'Back': 'arrow-left',
  'Search': 'magnify',
  'Upload': 'upload',
  'Download': 'download',
  'Setting': 'cog',
  'QuestionFilled': 'help-circle',
  'Box': 'box',
  'VideoPlay': 'play',
  'VideoPause': 'pause',
  'Remove': 'remove',
  'DataAnalysis': 'chart-bar',
  'FullScreen': 'fullscreen',
  'Timer': 'timer',
  'HomeFilled': 'home',
  'TrendCharts': 'chart-line',
  'Tools': 'wrench',
}

export function getMdiIconPath(name: IconName | string): string {
  return iconMap[name] || ''
}

export function fromElementPlusIcon(iconName: string): IconName {
  return elementPlusToMdiMap[iconName] || 'alert-circle'
}
