/**
 * 图标映射工具单元测试
 * 测试图标名称映射、Element Plus 到 MDI 图标转换以及路径获取
 */
import { describe, it, expect } from 'vitest'
import { iconMap, elementPlusToMdiMap, getMdiIconPath, fromElementPlusIcon } from '@/utils/icon-map'

describe('图标映射工具', () => {
  describe('iconMap', () => {
    it('应该是一个非空对象', () => {
      expect(iconMap).toBeDefined()
      expect(typeof iconMap).toBe('object')
      expect(Object.keys(iconMap).length).toBeGreaterThan(0)
    })

    it('应该包含 refresh 图标', () => {
      expect(iconMap).toHaveProperty('refresh')
      expect(typeof iconMap['refresh']).toBe('string')
      expect(iconMap['refresh'].length).toBeGreaterThan(0)
    })

    it('应该包含 close 图标', () => {
      expect(iconMap).toHaveProperty('close')
      expect(typeof iconMap['close']).toBe('string')
    })

    it('应该包含 connection 图标', () => {
      expect(iconMap).toHaveProperty('connection')
      expect(typeof iconMap['connection']).toBe('string')
    })

    it('应该包含 key 图标', () => {
      expect(iconMap).toHaveProperty('key')
      expect(typeof iconMap['key']).toBe('string')
    })

    it('应该包含 delete 图标', () => {
      expect(iconMap).toHaveProperty('delete')
      expect(typeof iconMap['delete']).toBe('string')
    })

    it('应该包含 folder-open 图标', () => {
      expect(iconMap).toHaveProperty('folder-open')
      expect(typeof iconMap['folder-open']).toBe('string')
    })

    it('应该包含 plus 图标', () => {
      expect(iconMap).toHaveProperty('plus')
      expect(typeof iconMap['plus']).toBe('string')
    })

    it('应该包含 check 图标', () => {
      expect(iconMap).toHaveProperty('check')
      expect(typeof iconMap['check']).toBe('string')
    })

    it('应该包含 check-circle 图标', () => {
      expect(iconMap).toHaveProperty('check-circle')
      expect(typeof iconMap['check-circle']).toBe('string')
    })

    it('应该包含 monitor 图标', () => {
      expect(iconMap).toHaveProperty('monitor')
      expect(typeof iconMap['monitor']).toBe('string')
    })

    it('应该包含 information 图标', () => {
      expect(iconMap).toHaveProperty('information')
      expect(typeof iconMap['information']).toBe('string')
    })

    it('应该包含 cpu 图标', () => {
      expect(iconMap).toHaveProperty('cpu')
      expect(typeof iconMap['cpu']).toBe('string')
    })

    it('应该包含 folder 图标', () => {
      expect(iconMap).toHaveProperty('folder')
      expect(typeof iconMap['folder']).toBe('string')
    })

    it('应该包含 loading 图标', () => {
      expect(iconMap).toHaveProperty('loading')
      expect(typeof iconMap['loading']).toBe('string')
    })

    it('应该包含 pencil 图标', () => {
      expect(iconMap).toHaveProperty('pencil')
      expect(typeof iconMap['pencil']).toBe('string')
    })

    it('应该包含 alert 图标', () => {
      expect(iconMap).toHaveProperty('alert')
      expect(typeof iconMap['alert']).toBe('string')
    })

    it('应该包含 alert-circle 图标', () => {
      expect(iconMap).toHaveProperty('alert-circle')
      expect(typeof iconMap['alert-circle']).toBe('string')
    })

    it('应该包含 arrow-up 图标', () => {
      expect(iconMap).toHaveProperty('arrow-up')
      expect(typeof iconMap['arrow-up']).toBe('string')
    })

    it('应该包含 magnify 图标', () => {
      expect(iconMap).toHaveProperty('magnify')
      expect(typeof iconMap['magnify']).toBe('string')
    })

    it('应该包含 upload 图标', () => {
      expect(iconMap).toHaveProperty('upload')
      expect(typeof iconMap['upload']).toBe('string')
    })

    it('应该包含 download 图标', () => {
      expect(iconMap).toHaveProperty('download')
      expect(typeof iconMap['download']).toBe('string')
    })

    it('应该包含 cog 图标', () => {
      expect(iconMap).toHaveProperty('cog')
      expect(typeof iconMap['cog']).toBe('string')
    })

    it('应该包含 home 图标', () => {
      expect(iconMap).toHaveProperty('home')
      expect(typeof iconMap['home']).toBe('string')
    })

    it('应该包含 store 图标', () => {
      expect(iconMap).toHaveProperty('store')
      expect(typeof iconMap['store']).toBe('string')
    })

    it('应该包含 play 图标', () => {
      expect(iconMap).toHaveProperty('play')
      expect(typeof iconMap['play']).toBe('string')
    })

    it('应该包含 pause 图标', () => {
      expect(iconMap).toHaveProperty('pause')
      expect(typeof iconMap['pause']).toBe('string')
    })

    it('应该包含 fullscreen 图标', () => {
      expect(iconMap).toHaveProperty('fullscreen')
      expect(typeof iconMap['fullscreen']).toBe('string')
    })

    it('应该包含 fullscreen-exit 图标', () => {
      expect(iconMap).toHaveProperty('fullscreen-exit')
      expect(typeof iconMap['fullscreen-exit']).toBe('string')
    })

    it('应该包含 timer 图标', () => {
      expect(iconMap).toHaveProperty('timer')
      expect(typeof iconMap['timer']).toBe('string')
    })

    it('应该包含 chart-bar 图标', () => {
      expect(iconMap).toHaveProperty('chart-bar')
      expect(typeof iconMap['chart-bar']).toBe('string')
    })

    it('应该包含 chart-line 图标', () => {
      expect(iconMap).toHaveProperty('chart-line')
      expect(typeof iconMap['chart-line']).toBe('string')
    })

    it('应该包含 account 图标', () => {
      expect(iconMap).toHaveProperty('account')
      expect(typeof iconMap['account']).toBe('string')
    })

    it('应该包含 account-box 图标', () => {
      expect(iconMap).toHaveProperty('account-box')
      expect(typeof iconMap['account-box']).toBe('string')
    })

    it('应该包含 wrench 图标', () => {
      expect(iconMap).toHaveProperty('wrench')
      expect(typeof iconMap['wrench']).toBe('string')
    })

    it('应该包含 box 图标', () => {
      expect(iconMap).toHaveProperty('box')
      expect(typeof iconMap['box']).toBe('string')
    })

    it('应该包含 collection 图标', () => {
      expect(iconMap).toHaveProperty('collection')
      expect(typeof iconMap['collection']).toBe('string')
    })

    it('所有图标值都应该是非空字符串', () => {
      Object.entries(iconMap).forEach(([name, path]) => {
        expect(path).toBeTruthy()
        expect(typeof path).toBe('string')
        expect(path.length).toBeGreaterThan(0)
      })
    })
  })

  describe('elementPlusToMdiMap', () => {
    it('应该是一个非空对象', () => {
      expect(elementPlusToMdiMap).toBeDefined()
      expect(typeof elementPlusToMdiMap).toBe('object')
      expect(Object.keys(elementPlusToMdiMap).length).toBeGreaterThan(0)
    })

    it('应该将 Refresh 映射为 refresh', () => {
      expect(elementPlusToMdiMap['Refresh']).toBe('refresh')
    })

    it('应该将 Close 映射为 close', () => {
      expect(elementPlusToMdiMap['Close']).toBe('close')
    })

    it('应该将 CircleClose 映射为 close', () => {
      expect(elementPlusToMdiMap['CircleClose']).toBe('close')
    })

    it('应该将 Connection 映射为 connection', () => {
      expect(elementPlusToMdiMap['Connection']).toBe('connection')
    })

    it('应该将 Key 映射为 key', () => {
      expect(elementPlusToMdiMap['Key']).toBe('key')
    })

    it('应该将 Delete 映射为 delete', () => {
      expect(elementPlusToMdiMap['Delete']).toBe('delete')
    })

    it('应该将 FolderOpened 映射为 folder-open', () => {
      expect(elementPlusToMdiMap['FolderOpened']).toBe('folder-open')
    })

    it('应该将 DocumentCopy 映射为 content-copy', () => {
      expect(elementPlusToMdiMap['DocumentCopy']).toBe('content-copy')
    })

    it('应该将 SuccessFilled 映射为 check-circle', () => {
      expect(elementPlusToMdiMap['SuccessFilled']).toBe('check-circle')
    })

    it('应该将 Plus 映射为 plus', () => {
      expect(elementPlusToMdiMap['Plus']).toBe('plus')
    })

    it('应该将 Edit 映射为 pencil', () => {
      expect(elementPlusToMdiMap['Edit']).toBe('pencil')
    })

    it('应该将 Search 映射为 magnify', () => {
      expect(elementPlusToMdiMap['Search']).toBe('magnify')
    })

    it('应该将 Upload 映射为 upload', () => {
      expect(elementPlusToMdiMap['Upload']).toBe('upload')
    })

    it('应该将 Download 映射为 download', () => {
      expect(elementPlusToMdiMap['Download']).toBe('download')
    })

    it('应该将 Setting 映射为 cog', () => {
      expect(elementPlusToMdiMap['Setting']).toBe('cog')
    })

    it('应该将 Warning 映射为 alert', () => {
      expect(elementPlusToMdiMap['Warning']).toBe('alert')
    })

    it('应该将 HomeFilled 映射为 home', () => {
      expect(elementPlusToMdiMap['HomeFilled']).toBe('home')
    })

    it('应该将 Tools 映射为 wrench', () => {
      expect(elementPlusToMdiMap['Tools']).toBe('wrench')
    })

    it('所有映射值都应该存在于 iconMap 中', () => {
      Object.entries(elementPlusToMdiMap).forEach(([epName, mdiName]) => {
        expect(iconMap).toHaveProperty(mdiName)
      })
    })
  })

  describe('getMdiIconPath', () => {
    it('已知图标名应该返回对应的 SVG 路径', () => {
      const path = getMdiIconPath('refresh')
      expect(path).toBe(iconMap['refresh'])
      expect(path.length).toBeGreaterThan(0)
    })

    it('未知图标名应该返回空字符串', () => {
      const path = getMdiIconPath('nonexistent-icon' as any)
      expect(path).toBe('')
    })

    it('空字符串应该返回空字符串', () => {
      const path = getMdiIconPath('')
      expect(path).toBe('')
    })

    it('close 图标应该返回有效路径', () => {
      const path = getMdiIconPath('close')
      expect(path).toBeTruthy()
    })

    it('folder 图标应该返回有效路径', () => {
      const path = getMdiIconPath('folder')
      expect(path).toBeTruthy()
    })
  })

  describe('fromElementPlusIcon', () => {
    it('已知 Element Plus 图标应该返回对应的 MDI 图标名', () => {
      const result = fromElementPlusIcon('Refresh')
      expect(result).toBe('refresh')
    })

    it('Close 图标应该映射为 close', () => {
      const result = fromElementPlusIcon('Close')
      expect(result).toBe('close')
    })

    it('Edit 图标应该映射为 pencil', () => {
      const result = fromElementPlusIcon('Edit')
      expect(result).toBe('pencil')
    })

    it('未知图标应该返回默认值 alert-circle', () => {
      const result = fromElementPlusIcon('UnknownIcon')
      expect(result).toBe('alert-circle')
    })

    it('空字符串应该返回默认值', () => {
      const result = fromElementPlusIcon('')
      expect(result).toBe('alert-circle')
    })

    it('CircleCheck 应该映射为 check-circle', () => {
      const result = fromElementPlusIcon('CircleCheck')
      expect(result).toBe('check-circle')
    })

    it('User 应该映射为 account', () => {
      const result = fromElementPlusIcon('User')
      expect(result).toBe('account')
    })

    it('UserFilled 应该映射为 account-box', () => {
      const result = fromElementPlusIcon('UserFilled')
      expect(result).toBe('account-box')
    })

    it('DataAnalysis 应该映射为 chart-bar', () => {
      const result = fromElementPlusIcon('DataAnalysis')
      expect(result).toBe('chart-bar')
    })

    it('TrendCharts 应该映射为 chart-line', () => {
      const result = fromElementPlusIcon('TrendCharts')
      expect(result).toBe('chart-line')
    })

    it('Back 应该映射为 arrow-left', () => {
      const result = fromElementPlusIcon('Back')
      expect(result).toBe('arrow-left')
    })

    it('Top 应该映射为 arrow-up', () => {
      const result = fromElementPlusIcon('Top')
      expect(result).toBe('arrow-up')
    })

    it('返回的图标名应该在 iconMap 中存在', () => {
      const result = fromElementPlusIcon('Refresh')
      expect(iconMap).toHaveProperty(result)
    })
  })
})
