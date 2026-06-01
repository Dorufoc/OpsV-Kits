import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

vi.mock('@/components/md3', () => ({
  Md3Icon: { name: 'Md3Icon', props: ['name', 'size'], template: '<span class="mdi-icon" :data-name="name"></span>' },
  Md3Confirm: { show: vi.fn().mockResolvedValue(true) },
  Md3Message: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  Md3Dialog: { name: 'Md3Dialog', props: ['visible', 'title', 'width', 'closable'], emits: ['update:visible'], template: '<div class="md3-dialog" v-if="visible"><slot /><slot name="footer" /></div>' },
  Md3Input: { name: 'Md3Input', props: ['modelValue', 'label', 'placeholder', 'type', 'min', 'max', 'showPassword'], emits: ['update:modelValue'], template: '<input class="md3-input" :value="modelValue" :type="type" :placeholder="placeholder" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
  Md3Select: { name: 'Md3Select', props: ['modelValue', 'options', 'placeholder', 'label', 'clearable', 'size'], emits: ['update:modelValue'], template: '<select class="md3-select" :data-placeholder="placeholder">{{ placeholder }}</select>' },
  Md3Radio: { name: 'Md3Radio', props: ['modelValue', 'value', 'label'], emits: ['update:modelValue'], template: '<label class="md3-radio"><input type="radio" :value="value" :checked="modelValue === value" @change="$emit(\'update:modelValue\', value)" /><span>{{ label }}</span></label>' },
  Md3Checkbox: { name: 'Md3Checkbox', props: ['modelValue', 'label'], emits: ['update:modelValue'], template: '<label class="md3-checkbox"><input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" /><span>{{ label }}</span></label>' },
  Md3Divider: { name: 'Md3Divider', props: ['contentPosition'], template: '<hr class="md3-divider" />' },
}))

vi.mock('@/components/Md3Button.vue', () => ({
  default: { name: 'Md3Button', props: ['size', 'variant', 'disabled', 'icon', 'loading', 'type'], emits: ['click'], template: '<button class="md3-btn" :disabled="disabled" @click="$emit(\'click\')"><slot /></button>' },
}))

let sshStoreMock: any

vi.mock('@/stores/sshAccountStore', () => ({
  useSshAccountStore: () => sshStoreMock,
}))

vi.mock('@/api', () => ({
  request: {
    post: vi.fn().mockResolvedValue({ success: true, message: 'OK' }),
    get: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  sshStoreMock = {
    accounts: [
      { alias: 'test-server', host: '192.168.1.1', port: 22, default: true },
      { alias: 'prod-server', host: '10.0.0.1', port: 2222, default: false },
    ],
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
    testConnection: vi.fn().mockResolvedValue({ success: true, message: '连接成功' }),
  }
})

import WebSSHConnectDialog from '@/views/WebSSHConnectDialog.vue'

describe('WebSSHConnectDialog', () => {
  function createWrapper(props = {}) {
    return mount(WebSSHConnectDialog, {
      props: { visible: true, ...props },
      global: { stubs: { Md3Icon: true } },
    })
  }

  it('应该在 visible 为 true 时渲染对话框', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('.md3-dialog').exists()).toBe(true)
  })

  it('应该在 visible 为 false 时不渲染对话框', () => {
    const wrapper = createWrapper({ visible: false })
    expect(wrapper.find('.md3-dialog').exists()).toBe(false)
  })

  it('应该通过 Md3Dialog 的 title prop 传递标题', () => {
    const wrapper = createWrapper()
    const dialog = wrapper.findComponent({ name: 'Md3Dialog' })
    expect(dialog.props('title')).toBe('新建 SSH 连接')
  })

  it('应该默认选中 saved 连接模式', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.connectMode).toBe('saved')
  })

  it('应该在 saved 模式下渲染 SSH 账户选择器', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('SSH 账户')
  })

  it('切换到 manual 模式后应该显示手动输入表单', async () => {
    const wrapper = createWrapper()
    wrapper.vm.connectMode = 'manual'
    await nextTick()
    expect(wrapper.text()).toContain('主机地址')
    expect(wrapper.text()).toContain('用户名')
    expect(wrapper.text()).toContain('认证方式')
  })

  it('manual 模式下默认认证方式为密码', async () => {
    const wrapper = createWrapper()
    wrapper.vm.connectMode = 'manual'
    await nextTick()
    expect(wrapper.vm.manualForm.auth_type).toBe('password')
  })

  it('manual 模式下密码认证时应该显示密码输入框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.connectMode = 'manual'
    wrapper.vm.manualForm.auth_type = 'password'
    await nextTick()
    expect(wrapper.text()).toContain('密码')
  })

  it('manual 模式下密钥认证时应该显示私钥和密钥密码输入框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.connectMode = 'manual'
    wrapper.vm.manualForm.auth_type = 'key'
    await nextTick()
    expect(wrapper.text()).toContain('私钥文件')
    expect(wrapper.text()).toContain('密钥密码')
  })

  it('manual 模式下应该显示双因素认证输入框', async () => {
    const wrapper = createWrapper()
    wrapper.vm.connectMode = 'manual'
    await nextTick()
    expect(wrapper.text()).toContain('双因素认证')
    const totpInput = wrapper.findAll('.md3-input').find(i => i.attributes('placeholder') === 'TOTP 验证码')
    expect(totpInput).toBeTruthy()
  })

  it('应该渲染选项区域', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('保存此会话配置')
    expect(wrapper.text()).toContain('自动连接')
  })

  it('应该渲染终端设置区域', () => {
    const wrapper = createWrapper()
    const divider = wrapper.findComponent({ name: 'Md3Divider' })
    expect(divider.exists()).toBe(true)
    expect(wrapper.text()).toContain('主题')
    expect(wrapper.text()).toContain('字体')
    expect(wrapper.text()).toContain('字号')
    expect(wrapper.text()).toContain('编码')
  })

  it('默认终端设置应该正确', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.terminalSettings.theme).toBe('dark')
    expect(wrapper.vm.terminalSettings.font_family).toBe("'Fira Code', monospace")
    expect(wrapper.vm.terminalSettings.font_size).toBe(14)
    expect(wrapper.vm.terminalSettings.encoding).toBe('utf-8')
  })

  it('默认选项应该正确', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.options.save_session).toBe(true)
    expect(wrapper.vm.options.auto_connect).toBe(true)
  })

  it('buildConfig 在 saved 模式下应该包含 account_alias', () => {
    const wrapper = createWrapper()
    wrapper.vm.formData.account_alias = 'test-server'
    const config = wrapper.vm.buildConfig()
    expect(config.account_alias).toBe('test-server')
    expect(config.use_saved_account).toBe(true)
  })

  it('buildConfig 在 manual 模式下应该包含手动表单数据', () => {
    const wrapper = createWrapper()
    wrapper.vm.connectMode = 'manual'
    wrapper.vm.manualForm.host = '192.168.1.100'
    wrapper.vm.manualForm.port = 22
    wrapper.vm.manualForm.username = 'root'
    const config = wrapper.vm.buildConfig()
    expect(config.host).toBe('192.168.1.100')
    expect(config.port).toBe(22)
    expect(config.username).toBe('root')
    expect(config.use_saved_account).toBe(false)
  })

  it('buildConfig 应该包含选项和终端设置', () => {
    const wrapper = createWrapper()
    const config = wrapper.vm.buildConfig()
    expect(config.save_session).toBe(true)
    expect(config.auto_connect).toBe(true)
    expect(config.theme).toBe('dark')
    expect(config.font_family).toBe("'Fira Code', monospace")
    expect(config.font_size).toBe(14)
    expect(config.encoding).toBe('utf-8')
  })

  it('doConnect 应该触发 connect 事件', () => {
    const wrapper = createWrapper()
    wrapper.vm.doConnect()
    expect(wrapper.emitted('connect')).toBeTruthy()
    expect(wrapper.emitted('connect')![0][0]).toHaveProperty('use_saved_account')
  })

  it('取消按钮应该触发 update:visible 事件', async () => {
    const wrapper = createWrapper()
    const buttons = wrapper.findAll('.md3-btn')
    const cancelButton = buttons.find(b => b.text().includes('取消'))
    if (cancelButton) {
      await cancelButton.trigger('click')
      expect(wrapper.emitted('update:visible')).toBeTruthy()
      expect(wrapper.emitted('update:visible')![0][0]).toBe(false)
    }
  })

  it('testConnection 在 saved 模式下应该调用 sshStore.testConnection', async () => {
    const wrapper = createWrapper()
    wrapper.vm.formData.account_alias = 'test-server'
    await wrapper.vm.testConnection()
    expect(sshStoreMock.testConnection).toHaveBeenCalledWith('test-server')
  })

  it('testConnection 在 saved 模式成功时应该显示成功消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    const wrapper = createWrapper()
    wrapper.vm.formData.account_alias = 'test-server'
    await wrapper.vm.testConnection()
    expect(Md3Message.success).toHaveBeenCalled()
  })

  it('testConnection 在 saved 模式失败时应该显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    sshStoreMock.testConnection = vi.fn().mockResolvedValue({ success: false, message: '连接失败' })
    const wrapper = createWrapper()
    wrapper.vm.formData.account_alias = 'test-server'
    await wrapper.vm.testConnection()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('testConnection 在 manual 模式下应该调用 request.post', async () => {
    const { request } = await import('@/api')
    const wrapper = createWrapper()
    wrapper.vm.connectMode = 'manual'
    wrapper.vm.manualForm.host = '192.168.1.100'
    await wrapper.vm.testConnection()
    expect(request.post).toHaveBeenCalledWith('/webssh/test', expect.any(Object))
  })

  it('testConnection 异常时应该显示错误消息', async () => {
    const { Md3Message } = await import('@/components/md3')
    sshStoreMock.testConnection = vi.fn().mockRejectedValue(new Error('网络错误'))
    const wrapper = createWrapper()
    wrapper.vm.formData.account_alias = 'test-server'
    await wrapper.vm.testConnection()
    expect(Md3Message.error).toHaveBeenCalled()
  })

  it('testing 状态应该在 testConnection 期间正确切换', async () => {
    let resolveTest: Function
    sshStoreMock.testConnection = vi.fn().mockImplementation(() => new Promise(r => { resolveTest = r }))
    const wrapper = createWrapper()
    wrapper.vm.formData.account_alias = 'test-server'
    const promise = wrapper.vm.testConnection()
    expect(wrapper.vm.testing).toBe(true)
    resolveTest!({ success: true })
    await promise
    expect(wrapper.vm.testing).toBe(false)
  })

  it('onMounted 应该调用 fetchAccounts', () => {
    createWrapper()
    expect(sshStoreMock.fetchAccounts).toHaveBeenCalled()
  })

  it('accounts 计算属性应该返回 sshStore 的账户列表', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.accounts).toHaveLength(2)
    expect(wrapper.vm.accounts[0].alias).toBe('test-server')
  })

  it('manual 模式下 manualForm 默认值应该正确', async () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.manualForm.host).toBe('')
    expect(wrapper.vm.manualForm.port).toBe(22)
    expect(wrapper.vm.manualForm.username).toBe('')
    expect(wrapper.vm.manualForm.auth_type).toBe('password')
    expect(wrapper.vm.manualForm.password).toBe('')
    expect(wrapper.vm.manualForm.private_key).toBe('')
    expect(wrapper.vm.manualForm.key_passphrase).toBe('')
    expect(wrapper.vm.manualForm.totp_code).toBe('')
  })
})
