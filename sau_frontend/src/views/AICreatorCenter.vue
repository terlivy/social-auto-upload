<template>
  <div class="ai-creator-center">
    <div class="page-header">
      <h2>🤖 AI 创作者中心</h2>
      <p class="subtitle">输入素材，AI 自动生成提示词、标题、话题建议</p>
    </div>

    <div class="main-content">
      <!-- 左侧：素材输入区 -->
      <div class="input-panel">
        <el-card shadow="never" class="input-card">
          <template #header>
            <div class="card-header">
              <span>📦 素材输入</span>
            </div>
          </template>

          <!-- 素材类型选择 -->
          <div class="material-type-section">
            <span class="section-label">素材类型</span>
            <el-radio-group v-model="materialType" size="default" class="type-radios">
              <el-radio-button value="url">🔗 链接</el-radio-button>
              <el-radio-button value="image">🖼️ 图片</el-radio-button>
              <el-radio-button value="text">📝 文本</el-radio-button>
              <el-radio-button value="video">🎬 视频</el-radio-button>
            </el-radio-group>
          </div>

          <!-- 平台选择 -->
          <div class="platform-section">
            <span class="section-label">目标平台</span>
            <el-radio-group v-model="platform" size="default" class="platform-radios">
              <el-radio-button value="douyin">🎵 抖音</el-radio-button>
              <el-radio-button value="xiaohongshu">📕 小红书</el-radio-button>
            </el-radio-group>
          </div>

          <!-- 链接输入 -->
          <div v-if="materialType === 'url'" class="input-section">
            <el-input
              v-model="urlInput"
              type="textarea"
              :rows="4"
              placeholder="请输入素材链接，如：https://example.com/video.mp4"
              clearable
            />
          </div>

          <!-- 图片上传 -->
          <div v-if="materialType === 'image'" class="input-section">
            <el-upload
              class="image-uploader"
              drag
              :auto-upload="false"
              :show-file-list="true"
              accept="image/*"
              :on-change="handleImageChange"
              :limit="1"
            >
              <div v-if="!imagePreview">
                <el-icon class="el-icon--upload"><Upload /></el-icon>
                <div class="el-upload__text">拖拽图片到此处，或<em>点击上传</em></div>
                <div class="upload-tip">支持 JPG、PNG、WebP，不超过 10MB</div>
              </div>
              <div v-else class="image-preview-wrapper">
                <img :src="imagePreview" class="image-preview" />
                <el-button type="danger" size="small" class="remove-image-btn" @click.stop="removeImage">
                  删除
                </el-button>
              </div>
            </el-upload>
          </div>

          <!-- 文本输入 -->
          <div v-if="materialType === 'text'" class="input-section">
            <el-input
              v-model="textInput"
              type="textarea"
              :rows="6"
              placeholder="请输入文本素材，如：产品介绍文案、活动描述、故事大纲..."
              clearable
            />
          </div>

          <!-- 视频上传 -->
          <div v-if="materialType === 'video'" class="input-section">
            <el-upload
              class="video-uploader"
              drag
              :auto-upload="false"
              :show-file-list="true"
              accept="video/*"
              :on-change="handleVideoChange"
              :limit="1"
            >
              <div v-if="!videoFile">
                <el-icon class="el-icon--upload"><VideoPlayer /></el-icon>
                <div class="el-upload__text">拖拽视频到此处，或<em>点击上传</em></div>
                <div class="upload-tip">支持 MP4、AVI、MOV，不超过 500MB</div>
              </div>
              <div v-else class="video-preview-wrapper">
                <span class="video-name">{{ videoFile.name }}</span>
                <span class="video-size">{{ (videoFile.size / 1024 / 1024).toFixed(2) }} MB</span>
                <el-button type="danger" size="small" @click.stop="removeVideo">
                  删除
                </el-button>
              </div>
            </el-upload>
          </div>

          <!-- 生成按钮 -->
          <div class="action-section">
            <el-button
              type="primary"
              size="large"
              :loading="generating"
              :disabled="!canGenerate"
              class="generate-btn"
              @click="generateContent"
            >
              {{ generating ? '🤖 AI 分析中...' : '✨ 生成内容方案' }}
            </el-button>
            <el-button size="large" @click="resetForm" :disabled="generating">
              重置
            </el-button>
          </div>
        </el-card>
      </div>

      <!-- 右侧：AI 输出区 -->
      <div class="output-panel">
        <el-card shadow="never" class="output-card" v-if="generatedContent">
          <template #header>
            <div class="card-header">
              <span>📋 AI 生成结果</span>
              <div class="header-actions">
                <el-button size="small" @click="copyAll">复制全部</el-button>
              </div>
            </div>
          </template>

          <!-- 视频提示词 -->
          <div v-if="parsedResult.prompt" class="result-section">
            <div class="section-title">
              <span>🎬 视频提示词</span>
              <el-button size="small" @click="copyText(parsedResult.prompt)">复制</el-button>
            </div>
            <div class="prompt-box">{{ parsedResult.prompt }}</div>
          </div>

          <!-- 标题建议 -->
          <div v-if="parsedResult.titles && parsedResult.titles.length" class="result-section">
            <div class="section-title">
              <span>📣 标题建议</span>
              <el-button size="small" @click="copyText(parsedResult.titles.join('\n'))">复制</el-button>
            </div>
            <div class="titles-list">
              <div
                v-for="(title, idx) in parsedResult.titles"
                :key="idx"
                class="title-item"
                :class="{ active: selectedTitle === title }"
                @click="selectTitle(title)"
              >
                <span class="title-number">{{ idx + 1 }}</span>
                <span class="title-text">{{ title }}</span>
                <el-icon v-if="selectedTitle === title" class="check-icon"><Check /></el-icon>
              </div>
            </div>
          </div>

          <!-- 话题建议 -->
          <div v-if="parsedResult.topics && parsedResult.topics.length" class="result-section">
            <div class="section-title">
              <span>#️⃣ 话题建议</span>
              <el-button size="small" @click="copyText(parsedResult.topics.join(' '))">复制全部</el-button>
            </div>
            <div class="topics-cloud">
              <el-tag
                v-for="topic in parsedResult.topics"
                :key="topic"
                class="topic-tag"
                :class="{ selected: selectedTopics.includes(topic) }"
                @click="toggleTopic(topic)"
              >
                {{ topic }}
              </el-tag>
            </div>
          </div>

          <!-- 内容分析 -->
          <div v-if="parsedResult.analysis" class="result-section">
            <div class="section-title">
              <span>📊 内容分析</span>
            </div>
            <div class="analysis-box">
              <div v-if="parsedResult.analysis.selling_point" class="analysis-item">
                <span class="analysis-label">💡 核心卖点</span>
                <span class="analysis-value">{{ parsedResult.analysis.selling_point }}</span>
              </div>
              <div v-if="parsedResult.analysis.audience" class="analysis-item">
                <span class="analysis-label">👥 适合受众</span>
                <span class="analysis-value">{{ parsedResult.analysis.audience }}</span>
              </div>
              <div v-if="parsedResult.analysis.timing" class="analysis-item">
                <span class="analysis-label">⏰ 最佳时段</span>
                <span class="analysis-value">{{ parsedResult.analysis.timing }}</span>
              </div>
            </div>
          </div>

          <!-- 发送到发布中心 -->
          <div class="send-to-publish" v-if="hasOutput">
            <el-button type="success" size="large" @click="sendToPublishCenter">
              🚀 发送到发布中心
            </el-button>
          </div>
        </el-card>

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <div class="empty-icon">🤖</div>
          <div class="empty-text">输入素材后，AI 将自动分析并生成内容方案</div>
          <div class="empty-hint">支持：链接 / 图片 / 文本 / 视频</div>
        </div>

        <!-- 原始输出（调试用，可折叠） -->
        <el-collapse v-if="generatedContent && showRawOutput" class="raw-output-collapse">
          <el-collapse-item title="🔍 原始输出（点击展开）" name="raw">
            <pre class="raw-content">{{ generatedContent }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, VideoPlayer, Check } from '@element-plus/icons-vue'

// ============ 状态 ============
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'

const materialType = ref('url')
const platform = ref('douyin')
const urlInput = ref('')
const textInput = ref('')
const imageFile = ref(null)
const imagePreview = ref('')
const videoFile = ref(null)
const generating = ref(false)
const generatedContent = ref('')
const showRawOutput = ref(false)

// 解析后的结果
const parsedResult = reactive({
  prompt: '',
  titles: [],
  topics: [],
  analysis: {}
})

// 选中的标题/话题（用于发送到发布中心）
const selectedTitle = ref('')
const selectedTopics = ref([])

// ============ 计算属性 ============
const canGenerate = computed(() => {
  switch (materialType.value) {
    case 'url':
      return urlInput.value.trim().length > 0
    case 'image':
      return imageFile.value !== null
    case 'text':
      return textInput.value.trim().length > 0
    case 'video':
      return videoFile.value !== null
    default:
      return false
  }
})

const hasOutput = computed(() => {
  return parsedResult.prompt || parsedResult.titles.length || parsedResult.topics.length
})

// ============ 方法 ============

// 图片选择
const handleImageChange = (uploadFile, uploadFiles) => {
  const file = uploadFile.raw
  if (!file) return

  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 10MB')
    return
  }

  imageFile.value = file
  // 生成预览
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
  }
  reader.readAsDataURL(file)
}

const removeImage = () => {
  imageFile.value = null
  imagePreview.value = ''
}

// 视频选择
const handleVideoChange = (uploadFile, uploadFiles) => {
  const file = uploadFile.raw
  if (!file) return

  if (file.size > 500 * 1024 * 1024) {
    ElMessage.error('视频大小不能超过 500MB')
    return
  }

  videoFile.value = file
}

const removeVideo = () => {
  videoFile.value = null
}

// 重置表单
const resetForm = () => {
  urlInput.value = ''
  textInput.value = ''
  imageFile.value = null
  imagePreview.value = ''
  videoFile.value = null
  generatedContent.value = ''
  selectedTitle.value = ''
  selectedTopics.value = []
  Object.assign(parsedResult, { prompt: '', titles: [], topics: [], analysis: {} })
}

// 生成内容
const generateContent = async () => {
  if (!canGenerate.value) {
    ElMessage.warning('请先输入素材内容')
    return
  }

  generating.value = true
  generatedContent.value = ''

  try {
    let payload = {
      type: materialType.value,
      platform: platform.value,
      content: ''
    }

    if (materialType.value === 'url') {
      payload.content = urlInput.value.trim()
    } else if (materialType.value === 'image') {
      // base64 编码图片
      payload.content = imagePreview.value
    } else if (materialType.value === 'text') {
      payload.content = textInput.value.trim()
    } else if (materialType.value === 'video') {
      // 视频文件转 base64
      ElMessage.info('视频文件较大，转换中，请稍候...')
      payload.content = await fileToBase64(videoFile.value)
    }

    const response = await fetch(`${apiBaseUrl}/api/ai/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    const data = await response.json()

    if (!response.ok || !data.success) {
      throw new Error(data.error || '生成失败')
    }

    generatedContent.value = data.content
    parseGeneratedContent(data.content)

    ElMessage.success('✨ 内容生成成功！')

  } catch (error) {
    console.error('生成失败:', error)
    ElMessage.error(error.message || '生成失败，请重试')
  } finally {
    generating.value = false
  }
}

// 文件转 Base64
const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result)
    reader.onerror = (e) => reject(new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}

// 解析 AI 输出
const parseGeneratedContent = (content) => {
  // 解析 [PROMPT]...[/PROMPT]
  const promptMatch = content.match(/\[PROMPT\]\s*([\s\S]*?)\s*\[\/PROMPT\]/)
  // 解析 [TITLES]...[/TITLES]
  const titlesMatch = content.match(/\[TITLES\]\s*([\s\S]*?)\s*\[\/TITLES\]/)
  // 解析 [TOPICS]...[/TOPICS]
  const topicsMatch = content.match(/\[TOPICS\]\s*([\s\S]*?)\s*\[\/TOPICS\]/)
  // 解析 [ANALYSIS]...[/ANALYSIS]
  const analysisMatch = content.match(/\[ANALYSIS\]\s*([\s\S]*?)\s*\[\/ANALYSIS\]/)

  parsedResult.prompt = promptMatch ? promptMatch[1].trim() : ''
  parsedResult.titles = []

  if (titlesMatch) {
    const lines = titlesMatch[1].split('\n').filter(l => l.trim())
    for (const line of lines) {
      const match = line.match(/^\d+[．.、:：]\s*(.+)/)
      if (match) {
        parsedResult.titles.push(match[1].trim())
      }
    }
  }

  parsedResult.topics = []
  if (topicsMatch) {
    const topicsText = topicsMatch[1].trim()
    // 匹配 #话题名 格式
    const found = topicsText.match(/#[\w\u4e00-\u9fa5]+/g)
    if (found) {
      parsedResult.topics = found.map(t => t.replace(/^#/, ''))
    }
  }

  parsedResult.analysis = {}
  if (analysisMatch) {
    const analysisText = analysisMatch[1]
    const sellingMatch = analysisText.match(/卖点[：:]\s*(.+)/)
    const audienceMatch = analysisText.match(/受众[：:]\s*(.+)/)
    const timingMatch = analysisText.match(/时段[：:]\s*(.+)/)
    if (sellingMatch) parsedResult.analysis.selling_point = sellingMatch[1].trim()
    if (audienceMatch) parsedResult.analysis.audience = audienceMatch[1].trim()
    if (timingMatch) parsedResult.analysis.timing = timingMatch[1].trim()
  }
}

// 选择标题
const selectTitle = (title) => {
  selectedTitle.value = selectedTitle.value === title ? '' : title
}

// 切换话题选中
const toggleTopic = (topic) => {
  const idx = selectedTopics.value.indexOf(topic)
  if (idx >= 0) {
    selectedTopics.value.splice(idx, 1)
  } else {
    selectedTopics.value.push(topic)
  }
}

// 复制文本
const copyText = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// 复制全部
const copyAll = () => {
  let all = ''
  if (parsedResult.prompt) all += `[视频提示词]\n${parsedResult.prompt}\n\n`
  if (parsedResult.titles.length) all += `[标题建议]\n${parsedResult.titles.join('\n')}\n\n`
  if (parsedResult.topics.length) all += `[话题建议]\n${parsedResult.topics.map(t => '#' + t).join(' ')}\n\n`
  if (parsedResult.analysis.selling_point) all += `[分析]\n卖点：${parsedResult.analysis.selling_point}\n`
  if (parsedResult.analysis.audience) all += `受众：${parsedResult.analysis.audience}\n`
  if (parsedResult.analysis.timing) all += `时段：${parsedResult.analysis.timing}\n`
  copyText(all)
}

// 发送到发布中心
const sendToPublishCenter = () => {
  // 构建传递数据，存储到 sessionStorage，触发发布中心加载
  const data = {
    platform: platform.value,
    title: selectedTitle.value,
    topics: selectedTopics.value,
    prompt: parsedResult.prompt,
    rawContent: generatedContent.value
  }
  sessionStorage.setItem('aiCreatorData', JSON.stringify(data))
  ElMessage.success('已发送到发布中心，请在发布中心页面查看并使用')
  // 跳转到发布中心
  window.location.hash = '#/publish-center'
}
</script>

<style lang="scss" scoped>
.ai-creator-center {
  height: 100%;
  display: flex;
  flex-direction: column;

  .page-header {
    margin-bottom: 20px;

    h2 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 600;
    }

    .subtitle {
      margin: 0;
      color: #909399;
      font-size: 14px;
    }
  }

  .main-content {
    display: flex;
    gap: 20px;
    flex: 1;
    overflow: hidden;

    .input-panel {
      width: 400px;
      flex-shrink: 0;

      .input-card {
        height: 100%;
        overflow-y: auto;

        .card-header {
          font-weight: 600;
          font-size: 16px;
        }

        .section-label {
          display: block;
          font-size: 14px;
          font-weight: 500;
          color: #303133;
          margin-bottom: 10px;
        }

        .material-type-section,
        .platform-section {
          margin-bottom: 20px;
        }

        .type-radios,
        .platform-radios {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .input-section {
          margin-bottom: 20px;
        }

        // 图片上传
        .image-uploader {
          width: 100%;

          :deep(.el-upload) {
            width: 100%;
          }

          .image-preview-wrapper {
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;

            .image-preview {
              max-width: 100%;
              max-height: 200px;
              border-radius: 8px;
            }

            .remove-image-btn {
              position: absolute;
              top: 8px;
              right: 8px;
            }
          }
        }

        // 视频上传
        .video-uploader {
          width: 100%;

          .video-preview-wrapper {
            display: flex;
            align-items: center;
            gap: 12px;
            justify-content: center;
            padding: 12px;

            .video-name {
              font-size: 14px;
              color: #606266;
              max-width: 200px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }

            .video-size {
              font-size: 12px;
              color: #909399;
            }
          }
        }

        .upload-tip {
          font-size: 12px;
          color: #909399;
          margin-top: 8px;
        }

        .action-section {
          display: flex;
          gap: 10px;
          margin-top: 20px;

          .generate-btn {
            flex: 1;
          }
        }
      }
    }

    .output-panel {
      flex: 1;
      overflow-y: auto;

      .output-card {
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-weight: 600;
          font-size: 16px;
        }

        .result-section {
          margin-bottom: 24px;
          padding-bottom: 24px;
          border-bottom: 1px solid #f0f0f0;

          &:last-of-type {
            border-bottom: none;
          }

          .section-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            font-size: 15px;
            font-weight: 600;
            color: #303133;
          }

          .prompt-box {
            background: #f5f7fa;
            border-radius: 8px;
            padding: 16px;
            font-size: 14px;
            line-height: 1.8;
            color: #303133;
            white-space: pre-wrap;
          }

          .titles-list {
            display: flex;
            flex-direction: column;
            gap: 8px;

            .title-item {
              display: flex;
              align-items: center;
              gap: 10px;
              padding: 10px 14px;
              background: #f5f7fa;
              border-radius: 8px;
              cursor: pointer;
              transition: all 0.2s;

              &:hover {
                background: #ecf5ff;
              }

              &.active {
                background: #409eff;
                color: #fff;

                .title-number {
                  background: rgba(255, 255, 255, 0.3);
                  color: #fff;
                }
              }

              .title-number {
                background: #409eff;
                color: #fff;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: 600;
                flex-shrink: 0;
              }

              .title-text {
                flex: 1;
                font-size: 14px;
              }

              .check-icon {
                color: #fff;
              }
            }
          }

          .topics-cloud {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;

            .topic-tag {
              cursor: pointer;
              font-size: 13px;
              padding: 6px 12px;
              border-radius: 16px;
              transition: all 0.2s;

              &:hover {
                opacity: 0.8;
              }

              &.selected {
                background: #409eff;
                color: #fff;
                border-color: #409eff;
              }
            }
          }

          .analysis-box {
            background: #f5f7fa;
            border-radius: 8px;
            padding: 16px;

            .analysis-item {
              display: flex;
              gap: 12px;
              margin-bottom: 10px;

              &:last-child {
                margin-bottom: 0;
              }

              .analysis-label {
                font-weight: 600;
                color: #409eff;
                flex-shrink: 0;
              }

              .analysis-value {
                color: #303133;
                font-size: 14px;
              }
            }
          }
        }

        .send-to-publish {
          margin-top: 24px;
          text-align: center;
        }
      }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 400px;
        background: #fff;
        border-radius: 8px;
        border: 2px dashed #dcdfe6;

        .empty-icon {
          font-size: 64px;
          margin-bottom: 16px;
        }

        .empty-text {
          font-size: 16px;
          color: #606266;
          margin-bottom: 8px;
        }

        .empty-hint {
          font-size: 13px;
          color: #909399;
        }
      }

      .raw-output-collapse {
        margin-top: 12px;

        .raw-content {
          background: #1e1e1e;
          color: #d4d4d4;
          padding: 12px;
          border-radius: 4px;
          font-size: 12px;
          overflow-x: auto;
          white-space: pre-wrap;
          max-height: 300px;
          overflow-y: auto;
        }
      }
    }
  }
}
</style>
