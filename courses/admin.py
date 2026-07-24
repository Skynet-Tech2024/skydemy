{% extends "admin/change_list.html" %}
{% load i18n admin_urls static admin_list %}

{% block extrastyle %}
    {{ block.super }}
    <style>
        /* ----- Stat Cards ----- */
        .subject-stats {
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }
        .subject-stats .stat-card {
            flex: 1 1 180px;
            background: #ffffff;
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid #e5e7eb;
            text-align: center;
        }
        .subject-stats .stat-card .number {
            font-size: 28px;
            font-weight: 700;
            color: #0B7A3B;
            line-height: 1.2;
        }
        .subject-stats .stat-card .label {
            color: #4B5563;
            font-size: 14px;
            font-weight: 500;
            margin-top: 4px;
        }

        /* ----- Header ----- */
        .subject-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .subject-header h1 {
            font-size: 28px;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
        }
        .subject-header .btn-primary {
            background-color: #0B7A3B;
            color: #ffffff;
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        .subject-header .btn-primary:hover {
            background-color: #09632f;
            color: #ffffff;
        }

        /* ----- Search Bar ----- */
        .subject-search {
            margin-bottom: 20px;
        }
        .subject-search #searchbar {
            width: 100%;
            max-width: 500px;
            padding: 10px 16px 10px 40px;
            border: 1px solid #d1d5db;
            border-radius: 9999px;
            font-size: 15px;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: 12px center;
            background-size: 18px;
            color: #0f172a;
        }
        .subject-search #searchbar::placeholder {
            color: #9CA3AF;
        }

        /* ----- Action Buttons Bar ----- */
        .action-bar {
            background: #F8FAFC;
            border-radius: 12px;
            padding: 12px 20px;
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
            border: 1px solid #E5E7EB;
        }
        .action-bar .label {
            font-weight: 600;
            color: #1F2937;
            font-size: 14px;
            margin-right: 8px;
        }
        .action-bar .btn-action {
            border: none;
            padding: 6px 16px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            color: #ffffff;
            transition: opacity 0.2s;
        }
        .action-bar .btn-action:hover {
            opacity: 0.85;
        }
        .btn-approve {
            background-color: #16A34A;
        }
        .btn-reject {
            background-color: #DC2626;
        }
        .btn-delete {
            background-color: #EF4444;
        }
        #selected-count {
            color: #64748B;
            font-size: 13px;
            margin-left: auto;
        }

        /* ----- Table Container ----- */
        .subject-table {
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            overflow: auto;
            border: 1px solid #E5E7EB;
        }
        .subject-table table {
            width: 100%;
            border-collapse: collapse;
            min-width: 700px;
        }
        .subject-table thead th {
            background-color: #F8FAFC;
            border-bottom: 2px solid #E5E7EB;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            color: #1F2937;
            font-size: 13px;
        }
        .subject-table tbody td {
            padding: 12px 16px;
            border-bottom: 1px solid #F1F5F9;
            color: #1E293B;
            font-size: 14px;
        }
        .subject-table tbody tr:hover {
            background-color: #F8FAFC;
        }
        .subject-table tbody tr.selected {
            background-color: #e5f0fa !important;
        }
        .subject-table tbody tr.selected td {
            color: #1e293b !important;
        }

        /* ----- Status Badges ----- */
        .badge-status {
            padding: 2px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
        }
        .badge-status.approved {
            background: #D1FAE5;
            color: #065F46;
        }
        .badge-status.pending {
            background: #FEF3C7;
            color: #92400E;
        }
        .badge-status.rejected {
            background: #FEE2E2;
            color: #991B1B;
        }

        /* ----- Footer ----- */
        .subject-footer {
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid #E5E7EB;
            color: #6B7280;
            font-size: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .subject-footer .count {
            font-weight: 500;
            color: #0B7A3B;
        }

        /* ----- Hide default admin action dropdown ----- */
        .actions {
            display: none !important;
        }
    </style>
{% endblock %}

{% block content %}
<div id="content-main">

    <!-- ===== STAT CARDS ===== -->
    <div class="subject-stats">
        <div class="stat-card">
            <div class="number">{{ cl.result_count }}</div>
            <div class="label">Total Subjects</div>
        </div>
        <div class="stat-card">
            <div class="number">{{ pending_count|default:"0" }}</div>
            <div class="label">Pending</div>
        </div>
        <div class="stat-card">
            <div class="number">{{ approved_count|default:"0" }}</div>
            <div class="label">Approved</div>
        </div>
        <div class="stat-card">
            <div class="number">{{ rejected_count|default:"0" }}</div>
            <div class="label">Rejected</div>
        </div>
    </div>

    <!-- ===== HEADER ===== -->
    <div class="subject-header">
        <h1>📚 Subjects</h1>
        <div>
            {% if has_add_permission %}
                <a href="{% url 'admin:courses_subject_add' %}" class="btn-primary">+ New Subject</a>
            {% endif %}
        </div>
    </div>

    <!-- ===== SEARCH ===== -->
    <div class="subject-search">
        {% block search %}
            {{ block.super }}
        {% endblock %}
    </div>

    <!-- ===== FORM ===== -->
    <form id="changelist-form" method="post" action="">
        {% csrf_token %}
        <input type="hidden" name="action" id="action-input" value="">

        <!-- ===== ACTION BUTTONS BAR ===== -->
        <div class="action-bar">
            <span class="label">Actions:</span>
            <button type="button" class="btn-action btn-approve" onclick="batchAction('approve_subjects')">✅ Approve</button>
            <button type="button" class="btn-action btn-reject" onclick="batchAction('reject_subjects')">❌ Reject</button>
            <button type="button" class="btn-action btn-delete" onclick="batchAction('delete_selected_subjects')">🗑️ Delete</button>
            <span id="selected-count">0 selected</span>
        </div>

        <!-- ===== TABLE ===== -->
        <div class="subject-table">
            {% block result_list %}
                {% result_list cl %}
            {% endblock %}
        </div>
    </form>

    <!-- ===== FOOTER ===== -->
    <div class="subject-footer">
        <span>
            Showing <span class="count">{{ cl.result_count }}</span> subject{{ cl.result_count|pluralize }}
        </span>
        <span>
            {% if cl.paginator.num_pages > 1 %}
                Page {{ cl.page_num }} of {{ cl.paginator.num_pages }}
            {% endif %}
        </span>
    </div>

    <!-- ===== PAGINATION ===== -->
    {% block pagination %}
        {{ block.super }}
    {% endblock %}

</div>

<!-- ===== SweetAlert2 ===== -->
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
<script>
    // ===== UPDATE SELECTED COUNT =====
    function updateSelectedCount() {
        const checkboxes = document.querySelectorAll('#result_list tbody input[type="checkbox"][name="_selected_action"]:checked');
        document.getElementById('selected-count').textContent = checkboxes.length + ' selected';
    }

    // ===== SELECT ALL / DESELECT ALL =====
    document.addEventListener('DOMContentLoaded', function() {
        const selectAll = document.querySelector('#result_list thead input[type="checkbox"]');
        if (selectAll) {
            selectAll.addEventListener('change', function() {
                const checkboxes = document.querySelectorAll('#result_list tbody input[type="checkbox"][name="_selected_action"]');
                checkboxes.forEach(cb => cb.checked = this.checked);
                updateSelectedCount();
            });
        }
        // Update count on any checkbox change
        document.querySelectorAll('#result_list tbody input[type="checkbox"][name="_selected_action"]').forEach(cb => {
            cb.addEventListener('change', updateSelectedCount);
        });
        updateSelectedCount();
    });

    // ===== BATCH ACTION =====
    function batchAction(action) {
        const checkboxes = document.querySelectorAll('#result_list tbody input[type="checkbox"][name="_selected_action"]:checked');
        if (checkboxes.length === 0) {
            Swal.fire({
                icon: 'warning',
                title: 'No Subjects Selected',
                text: 'Please select at least one subject.',
                confirmButtonColor: '#0B7A3B',
            });
            return;
        }

        const actionLabels = {
            'approve_subjects': 'Approve',
            'reject_subjects': 'Reject',
            'delete_selected_subjects': 'Delete'
        };
        const actionIcons = {
            'approve_subjects': '✅',
            'reject_subjects': '❌',
            'delete_selected_subjects': '🗑️'
        };
        const actionColors = {
            'approve_subjects': '#16A34A',
            'reject_subjects': '#DC2626',
            'delete_selected_subjects': '#EF4444'
        };
        const isDestructive = (action === 'delete_selected_subjects');

        Swal.fire({
            title: `${actionIcons[action]} ${actionLabels[action]} Subjects?`,
            text: `You are about to ${actionLabels[action].toLowerCase()} ${checkboxes.length} selected subject(s). ${isDestructive ? 'This action cannot be undone!' : ''}`,
            icon: isDestructive ? 'warning' : 'question',
            showCancelButton: true,
            confirmButtonColor: actionColors[action],
            cancelButtonColor: '#6c757d',
            confirmButtonText: `Yes, ${actionLabels[action].toLowerCase()} them`,
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                document.getElementById('action-input').value = action;
                document.getElementById('changelist-form').submit();
            }
        });
    }
</script>
{% endblock %}