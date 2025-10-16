(() => {
  const root = document.querySelector('[data-results-root]');
  if (!root) {
    return;
  }

  const taskId = root.dataset.taskId || '';
  const defaultDatasetUrl = root.dataset.defaultDatasetUrl || '';
  const defaultDownloadUrl = root.dataset.defaultDownloadUrl || '';
  const statusUrl = root.dataset.statusUrl || '';
  const streamUrl = root.dataset.streamUrl || '';
  let datasetUrl = root.dataset.datasetUrl || '';
  let currentStatus = root.dataset.status || 'PENDING';
  let currentProgress = Number(root.dataset.progress || 0);
  let processedRecords = Number(root.dataset.processed || 0);
  let totalRecords = Number(root.dataset.total || 0);

  const STATUS_LABELS = {
    PENDING: 'В очереди',
    PROCESSING: 'Обработка',
    COMPLETED: 'Готово',
    FAILED: 'Ошибка',
    NOT_FOUND: 'Не найдена',
  };

  const ARSHIN_BASE_URL = 'https://fgis.gost.ru/fundmetrology/cm/results/';
  const STATUS_FETCH_TIMEOUT_MS = 9000;
  const HEARTBEAT_INTERVAL_MS = 6000;

  const terminalPanel = document.getElementById('terminalPanel');
  const terminalLog = document.getElementById('terminalLog');
  const progressLabel = document.getElementById('progressLabel');
  const statusLabelNode = document.getElementById('statusLabel');
  const tablePanel = document.getElementById('tablePanel');
  const downloadLink = document.getElementById('downloadLink');
  const downloadHref = downloadLink ? downloadLink.dataset.downloadHref || defaultDownloadUrl : defaultDownloadUrl;
  const visibleCounter = document.getElementById('visibleCount');
  const progressDetailed = document.getElementById('progressDetailed');
  const progressFill = document.getElementById('terminalProgressFill');
  const headerRow = document.getElementById('resultsHeaderRow');
  const filterRow = document.getElementById('resultsFilterRow');
  const tableBody = document.getElementById('resultsTableBody');
  const emptyState = document.getElementById('emptyState');
  const resetBtn = document.getElementById('resetTableBtn');

  const summaryNodes = {
    processed: document.getElementById('summaryTotal'),
    updated: document.getElementById('summaryUpdated'),
    unchanged: document.getElementById('summaryUnchanged'),
    not_found: document.getElementById('summaryMissing'),
    duration: document.getElementById('summaryDuration'),
  };
  const chipRefs = {
    updated: null,
    unchanged: null,
    not_found: null,
  };
  let rawRecords = [];
  let filteredRecords = [];
  const filters = {};
  let currentSort = { key: null, direction: 'none' };
  let pollingHandle = null;
  let eventSource = null;
  let sseActive = false;
  const LOG_HISTORY_LIMIT = 500;
  const logCache = new Set();
  const logOrder = [];
  let tableInitialized = false;
  let datasetLoaded = false;
  let datasetLoading = false;
  let lastLoggedProgress = null;
  let lastLoggedStatus = null;
  let lastLoggedProcessed = null;
  let lastSummarySnapshot = null;
  let terminalInitialized = false;
  let completionSummaryLogged = false;
  let failureLogged = false;
  let idleWarningLogged = false;
  let lastProgressChange = Date.now();
  let lastStatusErrorLoggedAt = 0;

  initializeTerminal();
  recordLogEntry(currentProgress, currentStatus);

  const STATUS_CONFIG = {
    updated: { label: 'Обновлено', className: 'status-chip status-chip--updated', rank: 0 },
    updated_uncertain: { label: 'Обновлено?', className: 'status-chip status-chip--updated', rank: 0 },
    unchanged: { label: 'Без изменений', className: 'status-chip status-chip--unchanged', rank: 1 },
    not_found: { label: 'Не найдено', className: 'status-chip status-chip--missing', rank: 2 },
  };

  const columns = [
    { key: 'excel_source_row', label: 'Строка', type: 'number', align: 'right', sortable: true, filterable: true },
    {
      key: 'statusLabel',
      label: 'Статус',
      type: 'status',
      sortable: true,
      filterable: true,
      render: renderStatusCell,
      sortAccessor: record => STATUS_CONFIG[record.statusKind]?.rank ?? 99,
    },
    { key: 'result_docnum', label: 'Номер свидетельства', type: 'text', sortable: true, filterable: true },
    { key: 'arshin_id', label: 'ID в Аршине', type: 'link', sortable: true, filterable: true, render: renderArshinLinkCell },
    { key: 'mit_title', label: 'Наименование типа СИ', type: 'text', sortable: true, filterable: true },
    { key: 'mit_notation', label: 'Обозначение', type: 'text', sortable: true, filterable: true },
    { key: 'org_title', label: 'Организация', type: 'text', sortable: true, filterable: true },
    { key: 'mi_number', label: 'Заводской номер', type: 'text', sortable: true, filterable: true },
    {
      key: 'verification_date',
      label: 'Дата поверки',
      type: 'date',
      sortable: true,
      filterable: true,
      sortAccessor: record => record.verificationDateObj?.getTime() ?? Number.MIN_SAFE_INTEGER,
    },
    {
      key: 'valid_date',
      label: 'Действительна до',
      type: 'date',
      sortable: true,
      filterable: true,
      sortAccessor: record => record.validDateObj?.getTime() ?? Number.MIN_SAFE_INTEGER,
    },
    {
      key: 'period_range',
      label: 'Период поверки',
      type: 'date',
      sortable: true,
      filterable: true,
      sortAccessor: record => record.periodStartTime ?? Number.MIN_SAFE_INTEGER,
    },
    {
      key: 'intervalDisplay',
      label: 'Межповерочный интервал',
      type: 'interval',
      sortable: true,
      filterable: false,
      render: renderIntervalCell,
      sortAccessor: record => (Number.isFinite(record.intervalDays) ? record.intervalDays : Number.MIN_SAFE_INTEGER),
    },
  ];

  const columnsMap = Object.fromEntries(columns.map(column => [column.key, column]));

  const initialSummary = safeParseJSON(root.dataset.summary) || {};
  hydrateSummary(initialSummary);
  updateProgressUI(currentProgress, currentStatus, processedRecords, totalRecords);

  if (datasetUrl) {
    loadDataset();
  }

  if (statusUrl) {
    startStatusPolling();
  }
  if (streamUrl && typeof EventSource !== 'undefined') {
    initEventSource();
  }

  if (downloadLink && downloadLink.classList.contains('disabled') === false && downloadHref) {
    enableDownload();
  }

  function initEventSource() {
    if (!streamUrl || typeof EventSource === 'undefined') {
      return;
    }
    try {
      eventSource = new EventSource(streamUrl, { withCredentials: false });
      eventSource.onmessage = event => {
        try {
          const payload = JSON.parse(event.data);
          handleStreamPayload(payload);
        } catch (parseError) {
          console.warn('Stream payload parse error', parseError);
        }
      };
      eventSource.onopen = () => {
        sseActive = true;
        stopStatusPolling();
      pushLog('Подключение к каналу событий установлено.');
      };
      eventSource.onerror = error => {
        console.warn('Stream connection error', error);
        if (sseActive) {
      pushLog('⚠ Соединение с каналом событий потеряно. Перехожу к опросу статуса.');
        }
        sseActive = false;
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        if (statusUrl && !pollingHandle) {
          startStatusPolling();
        }
        setTimeout(() => {
          if (!eventSource && streamUrl) {
            initEventSource();
          }
        }, 3000);
      };
    } catch (err) {
      console.error('Failed to initialize EventSource', err);
      if (statusUrl) {
        startStatusPolling();
      }
    }
  }

  function startStatusPolling() {
    if (!statusUrl || pollingHandle) {
      return;
    }
    pollStatus();
    pollingHandle = setInterval(pollStatus, 1000);
  }

  function stopStatusPolling() {
    if (pollingHandle) {
      clearInterval(pollingHandle);
      pollingHandle = null;
    }
  }

  function pollStatus() {
    const controller = new AbortController();
    const timeoutHandle = setTimeout(() => controller.abort(), STATUS_FETCH_TIMEOUT_MS);

    fetch(statusUrl, {
      cache: 'no-store',
      signal: controller.signal,
    })
      .then(response => response.json())
      .then(payload => {
        clearTimeout(timeoutHandle);
        lastStatusErrorLoggedAt = 0;
        if (payload.error) {
          return;
        }

        const progress = Number(payload.progress ?? currentProgress);
        const status = payload.status || currentStatus;
        const processed = Number(payload.processed_records ?? processedRecords);
        const total = Number(payload.total_records ?? totalRecords);

        if (!Number.isNaN(processed)) {
          processedRecords = processed;
        }
        if (!Number.isNaN(total)) {
          totalRecords = total;
        }

        if (payload.summary && typeof payload.summary.total === 'number') {
          totalRecords = payload.summary.total;
        }

        updateProgressUI(progress, status, processedRecords, totalRecords);
        hydrateSummary(payload.summary || {});
        ingestLogs(payload);

        const summarySignature = JSON.stringify(payload.summary || {});
        if (summarySignature !== lastSummarySnapshot && summarySignature !== undefined) {
          lastSummarySnapshot = summarySignature;
          if (payload.summary && typeof payload.summary.processed === 'number') {
            const totalLabel = payload.summary.total ?? totalRecords ?? '—';
          pushLog(`Пройдено записей: ${payload.summary.processed}${totalLabel ? ` / ${totalLabel}` : ''}`);
          }
        }

        if (payload.dataset_available) {
          enableDownload();
          if (!datasetUrl) {
            datasetUrl = defaultDatasetUrl || (taskId ? `/api/v1/results/${taskId}/dataset` : '');
          }
        }

        const now = Date.now();
        if (status === 'PROCESSING' && now - lastProgressChange > 8000 && !idleWarningLogged) {
          pushLog('Ожидаю ответ от сервиса Аршин... возможны сетевые задержки.');
          idleWarningLogged = true;
        }

        if (status === 'COMPLETED') {
          if (!datasetLoaded) {
            loadDataset()
              .then(() => {
                updateProgressUI(100, 'COMPLETED', processedRecords, totalRecords);
                stopStatusPolling();
              })
              .catch(() => {
                /* retry on next poll */
              });
          } else {
            stopStatusPolling();
          }
        } else if (status === 'FAILED') {
          stopStatusPolling();
        }

        if (datasetUrl && !datasetLoaded && !datasetLoading && status !== 'FAILED') {
          loadDataset().catch(() => {
            /* swallow, retry next poll */
          });
        }
      })
      .catch(error => {
        clearTimeout(timeoutHandle);
        console.warn('Status polling error', error);
        const nowTs = Date.now();
        if (nowTs - lastStatusErrorLoggedAt >= HEARTBEAT_INTERVAL_MS) {
          pushLog('⚠ Не удалось получить статус задачи. Повторяю запрос...');
          lastStatusErrorLoggedAt = nowTs;
        }
      });
  }

  function handleStreamPayload(payload) {
    if (!payload || typeof payload !== 'object') {
      return;
    }

    const payloadType = payload.type || 'progress';

    if (payloadType === 'dataset') {
      if (payload.dataset_available) {
        datasetUrl = defaultDatasetUrl || datasetUrl || (taskId ? `/api/v1/results/${taskId}/dataset` : '');
        datasetLoaded = false;
        if (!datasetLoading) {
          loadDataset().catch(() => {
            /* swallow */
          });
        }
        enableDownload();
      }
      ingestLogs(payload);
      return;
    }

    if (payloadType === 'log') {
      if (payload.log) {
        pushLog(payload.log);
      }
      return;
    }

    const nextStatus = payload.status || currentStatus;
    const nextProgress = typeof payload.progress === 'number' ? payload.progress : currentProgress;
    const nextProcessed = typeof payload.processed === 'number' ? payload.processed : processedRecords;
    const nextTotal = typeof payload.total === 'number' ? payload.total : totalRecords;

    updateProgressUI(nextProgress, nextStatus, nextProcessed, nextTotal);

    if (payload.summary && typeof payload.summary === 'object') {
      hydrateSummary(payload.summary);
    }

    ingestLogs(payload);

    if (payload.dataset_available && !datasetLoaded) {
      datasetUrl = defaultDatasetUrl || datasetUrl || (taskId ? `/api/v1/results/${taskId}/dataset` : '');
      loadDataset().catch(() => {
        /* swallow */
      });
    }
    if (payload.result_available) {
      enableDownload();
    }
  }

  function ingestLogs(payload) {
    if (!payload || typeof payload !== 'object') {
      return;
    }
    const collected = [];
    if (Array.isArray(payload.log_messages)) {
      collected.push(...payload.log_messages);
    }
    if (Array.isArray(payload.logs)) {
      collected.push(...payload.logs);
    }
    if (typeof payload.log === 'string') {
      collected.push(payload.log);
    }
    if (typeof payload.last_log_message === 'string') {
      collected.push(payload.last_log_message);
    }
    if (payload.report) {
      const reportLine = renderReportLog(payload.report);
      if (reportLine) {
        collected.push(reportLine);
      }
    }
    collected.forEach(pushLog);
  }

  function loadDataset() {
    if (!datasetUrl || datasetLoaded || datasetLoading) {
      return Promise.resolve();
    }

    datasetLoading = true;
    return fetchDataset(datasetUrl)
      .then(payload => {
        if (!payload || !Array.isArray(payload.reports)) {
          throw new Error('Некорректный формат набора данных');
        }

        rawRecords = payload.reports.map(transformRecord);
        filteredRecords = [...rawRecords];
        hydrateSummary(payload.summary || {});

        if (!tableInitialized) {
          buildTableSkeleton();
          tableInitialized = true;
        }
        updateHeaderIndicators();
        renderTable();
        datasetLoaded = true;
        datasetLoading = false;
        processedRecords = rawRecords.length;
        if (!totalRecords) {
          totalRecords = rawRecords.length;
        }
        if (tablePanel) {
          tablePanel.hidden = false;
        }
        updateProgressUI(100, 'COMPLETED', processedRecords, totalRecords);
      pushLog('Набор данных загружен. Таблица готова к просмотру.');
    })
      .catch(error => {
        datasetLoading = false;
        console.error(error);
        showDatasetError('Не удалось загрузить данные предпросмотра. Повторная попытка...');
        pushLog('⚠ Не удалось загрузить предпросмотр данных. Ожидаю повторную попытку.');
        throw error;
      });
  }

  function enableDownload() {
    if (!downloadLink || !downloadHref) {
      return;
    }
    downloadLink.classList.remove('disabled');
    downloadLink.removeAttribute('aria-disabled');
    downloadLink.removeAttribute('role');
    downloadLink.href = downloadHref;
    downloadLink.setAttribute('download', '');
  }

  function fetchDataset(url) {
    return fetch(url, { headers: { Accept: 'application/json' } }).then(response => {
      if (!response.ok) {
        throw new Error(`Dataset request failed: ${response.status}`);
      }
      return response.json();
    });
  }

  function transformRecord(item, index) {
    const verificationDateObj = parseIsoDate(item.verification_date);
    const validDateObj = parseIsoDate(item.valid_date);
    const intervalInfo = calculateInterval(verificationDateObj, validDateObj);
    const periodRange = typeof item.period_range === 'string' ? item.period_range : '';
    const statusKind = resolveStatus(item);
    const statusMeta = STATUS_CONFIG[statusKind] || STATUS_CONFIG.not_found;
    const periodStartTime = verificationDateObj ? verificationDateObj.getTime() : null;

    const record = {
      ...item,
      excel_source_row: Number.parseInt(item.excel_source_row, 10) || index + 2,
      verificationDateObj,
      validDateObj,
      intervalDays: intervalInfo.days,
      intervalDisplay: intervalInfo.display,
      statusKind,
      statusLabel: statusMeta.label,
      arshinLink: item.arshin_id ? `${ARSHIN_BASE_URL}${item.arshin_id}` : null,
      period_range: periodRange,
      periodStartTime,
      filterMap: {},
    };

    columns.forEach(column => {
      if (column.filterable) {
        record.filterMap[column.key] = resolveFilterValue(record, column.key);
      }
    });

    return record;
  }

  function resolveStatus(item) {
    if (item.processing_status === 'NOT_FOUND' || !item.arshin_id) {
      return 'not_found';
    }
    if (item.processing_status === 'MATCHED' && item.certificate_updated) {
      return item.uncertain_update ? 'updated_uncertain' : 'updated';
    }
    if (item.processing_status === 'MATCHED') {
      return 'unchanged';
    }
    return 'not_found';
  }

  function resolveFilterValue(record, key) {
    if (key === 'statusLabel') {
      return record.statusLabel.toLowerCase();
    }
    if (key === 'arshin_id') {
      return (record.arshin_id || '').toString().toLowerCase();
    }
    const raw = record[key];
    if (raw === null || raw === undefined) {
      return '';
    }
    return String(raw).toLowerCase();
  }

  function buildTableSkeleton() {
    if (!headerRow || !filterRow) {
      return;
    }

    headerRow.innerHTML = '';
    filterRow.innerHTML = '';

    columns.forEach(column => {
      const th = document.createElement('th');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'header-control';
      button.dataset.sortKey = column.key;
      button.textContent = column.label;
      button.setAttribute('aria-label', `Сортировать по столбцу ${column.label}`);
      button.setAttribute('aria-sort', 'none');
      button.addEventListener('click', () => toggleSort(column.key));
      button.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          toggleSort(column.key);
        }
      });

      const indicator = document.createElement('span');
      indicator.className = 'sort-indicator';
      button.appendChild(indicator);

      th.appendChild(button);
      th.scope = 'col';
      th.setAttribute('role', 'columnheader');
      headerRow.appendChild(th);

      const filterCell = document.createElement('th');
      if (column.filterable) {
        const input = document.createElement('input');
        input.className = 'filter-input form-control form-control-sm';
        input.type = 'search';
        input.placeholder = 'Фильтр';
        input.setAttribute('aria-label', `Фильтрация по столбцу ${column.label}`);
        input.dataset.filterKey = column.key;
        input.addEventListener('input', debounce(event => {
          filters[column.key] = event.target.value.trim().toLowerCase();
          applyFiltersAndSort();
        }, 200));
        filterCell.appendChild(input);
      } else {
        filterCell.className = 'filter-placeholder';
      }
      filterRow.appendChild(filterCell);
    });

    if (resetBtn) {
      resetBtn.addEventListener('click', resetControls);
    }
  }

  function toggleSort(key) {
    if (!columnsMap[key]?.sortable) {
      return;
    }
    if (currentSort.key !== key) {
      currentSort = { key, direction: 'asc' };
    } else {
      currentSort.direction = currentSort.direction === 'asc' ? 'desc' : currentSort.direction === 'desc' ? 'none' : 'asc';
    }
    updateHeaderIndicators();
    applyFiltersAndSort();
  }

  function updateHeaderIndicators() {
    if (!headerRow) {
      return;
    }
    const buttons = headerRow.querySelectorAll('.header-control');
    buttons.forEach(button => {
      const key = button.dataset.sortKey;
      const indicator = button.querySelector('.sort-indicator');
      button.setAttribute('aria-sort', 'none');
      indicator.textContent = '';
      if (currentSort.key === key) {
        if (currentSort.direction === 'asc') {
          indicator.textContent = '▲';
          button.setAttribute('aria-sort', 'ascending');
        } else if (currentSort.direction === 'desc') {
          indicator.textContent = '▼';
          button.setAttribute('aria-sort', 'descending');
        } else {
          button.setAttribute('aria-sort', 'none');
        }
      }
    });
  }

  function applyFiltersAndSort() {
    if (!tableInitialized) {
      return;
    }
    filteredRecords = rawRecords.filter(record =>
      Object.entries(filters).every(([key, value]) => {
        if (!value) {
          return true;
        }
        return (record.filterMap[key] || '').includes(value);
      })
    );

    if (currentSort.key && currentSort.direction !== 'none') {
      const column = columnsMap[currentSort.key];
      const direction = currentSort.direction === 'asc' ? 1 : -1;
      const accessor = column.sortAccessor || (record => record[column.key]);

      filteredRecords.sort((a, b) => {
        const aValue = accessor(a);
        const bValue = accessor(b);
        return compareValues(aValue, bValue, column.type) * direction;
      });
    }

    renderTable();
  }

  function renderTable() {
    if (!tableBody) {
      return;
    }
    tableBody.innerHTML = '';

    if (!filteredRecords.length) {
      if (emptyState) {
        emptyState.hidden = false;
      }
      updateVisibleCounter(0);
      return;
    }

    if (emptyState) {
      emptyState.hidden = true;
    }
    const fragment = document.createDocumentFragment();
    filteredRecords.forEach(record => {
      const row = document.createElement('tr');
      columns.forEach(column => {
        const cell = document.createElement('td');
        if (column.align === 'right') {
          cell.classList.add('text-end');
        } else {
          cell.classList.add('text-start');
        }

        if (column.render) {
          column.render(cell, record);
        } else {
          const value = record[column.key];
          cell.textContent = formatCellValue(value, column.type);
        }
        row.appendChild(cell);
      });
      fragment.appendChild(row);
    });

    tableBody.appendChild(fragment);
    updateVisibleCounter(filteredRecords.length);
  }

  function updateVisibleCounter(count) {
    if (visibleCounter) {
      visibleCounter.textContent = count.toString();
    }
  }

  function renderStatusCell(cell, record) {
    const meta = STATUS_CONFIG[record.statusKind] || STATUS_CONFIG.not_found;
    const span = document.createElement('span');
    span.className = meta.className;
    span.textContent = meta.label;
    cell.appendChild(span);
  }

  function renderArshinLinkCell(cell, record) {
    if (record.arshin_id && record.arshinLink) {
      const link = document.createElement('a');
      link.href = record.arshinLink;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = record.arshin_id;
      link.className = 'external-link';
      cell.appendChild(link);
    } else {
      cell.textContent = '—';
      cell.classList.add('text-muted');
    }
  }

  function renderIntervalCell(cell, record) {
    if (record.intervalDisplay) {
      cell.textContent = record.intervalDisplay;
    } else {
      cell.textContent = '—';
      cell.classList.add('text-muted');
    }
  }

  function compareValues(a, b, type) {
    if (type === 'number' || type === 'interval') {
      const aNumber = Number(a);
      const bNumber = Number(b);
      if (Number.isNaN(aNumber) && Number.isNaN(bNumber)) return 0;
      if (Number.isNaN(aNumber)) return -1;
      if (Number.isNaN(bNumber)) return 1;
      return aNumber - bNumber;
    }

    if (type === 'date') {
      const aTime = a instanceof Date ? a.getTime() : Number.isFinite(a) ? a : Number.MIN_SAFE_INTEGER;
      const bTime = b instanceof Date ? b.getTime() : Number.isFinite(b) ? b : Number.MIN_SAFE_INTEGER;
      return aTime - bTime;
    }

    const aString = (a ?? '').toString().toLowerCase();
    const bString = (b ?? '').toString().toLowerCase();
    if (aString === bString) return 0;
    return aString > bString ? 1 : -1;
  }

  function formatCellValue(value, type) {
    if (value === null || value === undefined || value === '') {
      return '—';
    }
    if (type === 'number') {
      const num = Number(value);
      if (Number.isFinite(num)) {
        return Number.isInteger(num) ? num.toString() : num.toFixed(3);
      }
    }
    return value;
  }

  function updateProgressUI(progress, status, processed = null, total = null) {
    currentProgress = progress;
    currentStatus = status;
    if (typeof processed === 'number') {
      processedRecords = processed;
    }
    if (typeof total === 'number') {
      totalRecords = total;
    }

    const normalizedProgress = Math.max(0, Math.min(100, Math.round(progress)));
    if (progressLabel) {
      progressLabel.textContent = `${normalizedProgress}%`;
      progressLabel.dataset.status = status;
    }
    if (progressFill) {
      progressFill.style.width = `${normalizedProgress}%`;
    }
    if (statusLabelNode) {
      statusLabelNode.textContent = STATUS_LABELS[status] || status;
      statusLabelNode.dataset.status = status;
    }
    if (progressDetailed) {
      const totalLabel = totalRecords > 0 ? totalRecords : '—';
      progressDetailed.dataset.status = status;
      progressDetailed.textContent = totalRecords ? `${processedRecords} / ${totalLabel}` : `${processedRecords}`;
    }
    if (terminalPanel) {
      terminalPanel.dataset.status = status;
      terminalPanel.classList.toggle('terminal-panel--completed', status === 'COMPLETED');
      terminalPanel.classList.toggle('terminal-panel--failed', status === 'FAILED');
    }

    recordLogEntry(normalizedProgress, status);
  }

  function calculateInterval(startDate, endDate) {
    if (!startDate || !endDate || Number.isNaN(startDate) || Number.isNaN(endDate)) {
      return { days: null, display: null };
    }
    const diffMs = endDate.getTime() - startDate.getTime();
    if (!Number.isFinite(diffMs) || diffMs < 0) {
      return { days: null, display: null };
    }
    const days = Math.round(diffMs / (1000 * 60 * 60 * 24));
    if (!Number.isFinite(days) || days <= 0) {
      return { days: null, display: null };
    }
    const yearsApprox = days / 365;
    const yearsRounded = Math.round(yearsApprox);
    if (yearsRounded <= 0) {
      return { days, display: 'Менее года' };
    }
    return { days, display: `${yearsRounded} ${pluralizeYears(yearsRounded)}` };
  }

  function pluralizeYears(value) {
    const mod10 = value % 10;
    const mod100 = value % 100;
    if (mod10 === 1 && mod100 !== 11) {
      return 'год';
    }
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
      return 'года';
    }
    return 'лет';
  }

  function parseIsoDate(value) {
    if (typeof value !== 'string') {
      return null;
    }
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const isoPattern = /^\d{4}-\d{2}-\d{2}$/;
    const ruPattern = /^\d{2}\.\d{2}\.\d{4}$/;

    if (isoPattern.test(trimmed)) {
      const [year, month, day] = trimmed.split('-').map(Number);
      if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
        return null;
      }
      const parsedIso = new Date(Date.UTC(year, month - 1, day));
      return Number.isNaN(parsedIso.getTime()) ? null : parsedIso;
    }

    if (ruPattern.test(trimmed)) {
      const [day, month, year] = trimmed.split('.').map(Number);
      if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
        return null;
      }
      const parsedRu = new Date(Date.UTC(year, month - 1, day));
      return Number.isNaN(parsedRu.getTime()) ? null : parsedRu;
    }

    return null;
  }

  function formatDuration(value) {
    if (value === null || value === undefined) {
      return '—';
    }
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds < 0) {
      return '—';
    }
    if (seconds < 60) {
      return `${seconds.toFixed(2)} с`;
    }
    const minutes = Math.floor(seconds / 60);
    const residualSeconds = seconds % 60;
    if (minutes < 60) {
      return residualSeconds >= 1 ? `${minutes} мин ${Math.round(residualSeconds)} с` : `${minutes} мин`;
    }
    const hours = Math.floor(minutes / 60);
    const residualMinutes = minutes % 60;
    return residualMinutes > 0 ? `${hours} ч ${residualMinutes} мин` : `${hours} ч`;
  }

  function renderReportLog(report) {
    if (!report || typeof report !== 'object') {
      return null;
    }
    const rowLabel = report.excel_source_row ?? '—';
    const status = report.processing_status || '';
    const cert = report.result_docnum || report.source_certificate_number || '—';
    const miNumber = report.mi_number || 'без серийного номера';

    switch (status) {
      case 'MATCHED':
        if (report.certificate_updated && report.result_docnum) {
          return `Строка ${rowLabel}: обновлено свидетельство → ${report.result_docnum}`;
        }
        return `Строка ${rowLabel}: подтверждено свидетельство ${cert}`;
      case 'NOT_FOUND':
        return `Строка ${rowLabel}: запись не найдена (${miNumber})`;
      case 'INVALID_CERT_FORMAT':
        return `Строка ${rowLabel}: некорректный номер свидетельства ${cert}`;
      case 'ERROR':
        return `Строка ${rowLabel}: ошибка обработки`;
      default:
        return `Строка ${rowLabel}: обработка завершена`;
    }
  }

  function recordLogEntry(progressValue, statusValue) {
    if (!terminalLog) {
      return;
    }
    if (
      lastLoggedProgress === progressValue &&
      lastLoggedStatus === statusValue &&
      lastLoggedProcessed === processedRecords &&
      Date.now() - lastProgressChange < HEARTBEAT_INTERVAL_MS
    ) {
      return;
    }
    const statusText = STATUS_LABELS[statusValue] || statusValue;
    const totalLabel = totalRecords > 0 ? `${processedRecords}/${totalRecords}` : `${processedRecords}`;
    pushLog(`${statusText} · ${totalLabel} · ${progressValue}%`);
    lastLoggedProgress = progressValue;
    lastLoggedStatus = statusValue;
    lastLoggedProcessed = processedRecords;
    lastProgressChange = Date.now();
    idleWarningLogged = false;
    if (statusValue === 'FAILED' && !failureLogged) {
      pushLog('Обработка остановлена с ошибкой. Проверьте подробности в журнале.');
      failureLogged = true;
    }
    if (statusValue !== 'FAILED') {
      failureLogged = false;
    }
    if (statusValue !== 'COMPLETED') {
      completionSummaryLogged = false;
    }
  }

  function pushLog(message) {
    if (!message || typeof message !== 'string') {
      return;
    }
    if (logCache.has(message)) {
      return;
    }
    logCache.add(message);
    logOrder.push(message);
    if (logOrder.length > LOG_HISTORY_LIMIT) {
      const oldest = logOrder.shift();
      if (oldest) {
        logCache.delete(oldest);
      }
    }
    appendLogLine(message);
  }

  function appendLogLine(message) {
    if (!terminalLog) {
      return;
    }
    if (!terminalInitialized) {
      terminalLog.textContent = '';
      terminalInitialized = true;
    }
    const timestamp = formatTimestamp();
    terminalLog.textContent += `[${timestamp}] ${message}\n`;
    terminalLog.scrollTop = terminalLog.scrollHeight;
  }

  function formatTimestamp() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
  }

  function initializeTerminal() {
    if (terminalLog && !terminalInitialized) {
      terminalLog.textContent = '[--:--:--] Консоль инициализирована. Ожидание событий...\n';
      terminalInitialized = true;
    }
    completionSummaryLogged = false;
    failureLogged = false;
  }

  function debounce(callback, delay) {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => callback(...args), delay);
    };
  }

  function resetControls() {
    Object.keys(filters).forEach(key => {
      filters[key] = '';
    });
    filterRow.querySelectorAll('input[data-filter-key]').forEach(input => {
      input.value = '';
    });
    currentSort = { key: null, direction: 'none' };
    updateHeaderIndicators();
    applyFiltersAndSort();
  }

  function hydrateSummary(summary) {
    const processed = summary.processed ?? summary.total ?? 0;
    const updated = summary.updated ?? 0;
    const unchanged = summary.unchanged ?? 0;
    const notFound = summary.not_found ?? summary.missing ?? 0;
    const durationSeconds = summary.processing_time_seconds ?? summary.processing_time ?? null;

    if (summaryNodes.processed) summaryNodes.processed.textContent = processed;
    if (summaryNodes.updated) summaryNodes.updated.textContent = updated;
    if (summaryNodes.unchanged) summaryNodes.unchanged.textContent = unchanged;
    if (summaryNodes.not_found) summaryNodes.not_found.textContent = notFound;
    if (summaryNodes.duration) summaryNodes.duration.textContent = formatDuration(durationSeconds);

    if (chipRefs.updated) {
      chipRefs.updated.textContent = `Обновлено: ${updated}`;
    }
    if (chipRefs.unchanged) {
      chipRefs.unchanged.textContent = `Без изменений: ${unchanged}`;
    }
    if (chipRefs.not_found) {
      chipRefs.not_found.textContent = `Не найдено: ${notFound}`;
    }
    if (
      typeof durationSeconds === 'number' &&
      Number.isFinite(durationSeconds) &&
      currentStatus === 'COMPLETED' &&
      !completionSummaryLogged
    ) {
      pushLog(`Обработка завершена. Время выполнения: ${formatDuration(durationSeconds)}.`);
      completionSummaryLogged = true;
    }
  }

  function showDatasetError(message) {
    if (emptyState) {
      emptyState.hidden = false;
      emptyState.innerHTML = `<p>${message}</p>`;
    }
  }

  function safeParseJSON(value) {
    if (!value) return null;
    try {
      return JSON.parse(value);
    } catch (error) {
      console.warn('Failed to parse JSON dataset summary', error);
      return null;
    }
  }
})();
