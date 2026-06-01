<template>
  <div class="publish-records-page">
    <div class="page-header">
      <h2>📋 发布记录</h2>
      <div class="header-actions">
        <el-button @click="loadRecords" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filters">
      <el-select v-model="filterPlatform" placeholder="全部平台" clearable style="width:120px" @change="loadRecords">
        <el-option label="抖音" :value="3" />
        <el-option label="小红书" :value="1" />
        <el-option label="快手" :value="4" />
        <el-option label="视频号" :value="2" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width:120px" @change="loadRecords">
        <el-option label="成功" :value="1" />
        <el-option label="失败" :value="2" />
      </el-select>
      <el-date-picker
        v-model="filterDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width:240px"
        @change="loadRecords"
      />
      <el-input
        v-model="filterKeyword"
        placeholder="搜索标题"
        style="width:180px"
        clearable
        @input="debouncedLoad"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-num">{{ totalCount }}</span>
        <span class="stat-label">全部记录</span>
      </div>
      <div class="stat-card success">
        <span class="stat-num">{{ successCount }}</span>
        <span class="stat-label">成功</span>
      </div>
      <div class="stat-card danger">
        <span class="stat-num">{{ failCount }}</span>
        <span class="stat-label">失败</span>
      </div>
    </div>

    <!-- 记录列表 -->
    <el-table
      :data="records"
      v-loading="loading"
      stripe
      style="width:100%"
      empty-text="暂无发布记录"
    >
      <el-table-column label="时间" prop="created_at" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="标题" prop="title" min-width="180" show-overflow-tooltip />
      <el-table-column label="平台" prop="platform" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="platformType(row.platform)">
            {{ platformName(row.platform) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="账号" prop="account_name" width="120" show-overflow-tooltip />
      <el-table-column label="状态" prop="status" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.status === 1" type="success" size="small">成功</el-tag>
          <el-tag v-else-if="row.status === 2" type="danger" size="small">失败</el-tag>
          <el-tag v-else type="info" size="small">进行中</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="错误信息" prop="error_msg" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.error_msg" class="error-msg">{{ row.error_msg }}</span>
          <span v-else class="no-error">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="deleteRecord(row.id)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="totalCount"
        layout="total, sizes, prev, pager, next"
        @current-change="loadRecords"
        @size-change="loadRecords"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'

const records = ref([])
const loading = ref(false)
const totalCount = ref(0)
const successCount = ref(0)
const failCount = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterPlatform = ref('')
const filterStatus = ref('')
const filterDateRange = ref([])
const filterKeyword = ref('')

let debounceTimer = null
const debouncedLoad = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadRecords, 400)
}

const platformName = (k) => ({ 1: '小红书', 2: '视频号', 3: '抖音', 4: '快手' }[k] || k)
const platformType = (k) => ({ 1: 'danger', 2: 'warning', 3: '', 4: 'success' }[k] || 'info')

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getFullYear()}-${(d.getMonth()+1).toString().padStart(2,'0')}-${d.getDate().toString().padStart(2,'0')} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
}

const loadRecords = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: page.value,
      page_size: pageSize.value
    })
    if (filterPlatform.value) params.set('platform', filterPlatform.value)
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (filterKeyword.value) params.set('keyword', filterKeyword.value)
    if (filterDateRange.value?.length === 2) {
      params.set('start_date', filterDateRange.value[0])
      params.set('end_date', filterDateRange.value[1])
    }

    const res = await fetch(`${apiBaseUrl}/getPublishRecords?${params}`)
    const data = await res.json()
    if (data.code === 200) {
      records.value = data.data
      totalCount.value = data.total || data.data.length
      successCount.value = data.success_count || 0
      failCount.value = data.fail_count || 0
    }
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const deleteRecord = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除这条记录？', '提示', { type: 'warning' })
    const res = await fetch(`${apiBaseUrl}/deletePublishRecord?id=${id}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.code === 200) {
      ElMessage.success('已删除')
      loadRecords()
    } else {
      ElMessage.error('删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(loadRecords)
</script>

<style lang="scss" scoped>
.publish-records-page {
  padding: 20px;

  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }
  }

  .filters {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .stats-row {
    display: flex;
    gap: 16px;
    margin-bottom: 20px;

    .stat-card {
      background: #f5f7fa;
      border-radius: 8px;
      padding: 12px 24px;
      text-align: center;
      min-width: 100px;

      .stat-num {
        display: block;
        font-size: 24px;
        font-weight: 700;
        color: #303133;
      }

      .stat-label {
        font-size: 12px;
        color: #909399;
      }

      &.success .stat-num { color: #67c23a; }
      &.danger .stat-num { color: #f56c6c; }
    }
  }

  .error-msg {
    color: #f56c6c;
    font-size: 12px;
  }

  .no-error {
    color: #c0c4cc;
  }

  .pagination-wrapper {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
