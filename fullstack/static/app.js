const loginForm = document.getElementById('login-form');
const signupForm = document.getElementById('signup-form');
const showLogin = document.getElementById('show-login');
const showSignup = document.getElementById('show-signup');
const authSection = document.getElementById('auth-section');
const dashboard = document.getElementById('dashboard');
const adminPanel = document.getElementById('admin-panel');
const welcomeText = document.getElementById('welcome-text');
const roleText = document.getElementById('role-text');
const projectList = document.getElementById('project-list');
const taskList = document.getElementById('task-list');
const logoutBtn = document.getElementById('logout');

const authMessage = document.getElementById('auth-message');
const projectMessage = document.getElementById('project-message');
const taskMessage = document.getElementById('task-message');
const memberMessage = document.getElementById('member-message');

let currentUser = null;
let currentRole = null;
let token = null;

async function parseResponse(response) {
  const text = await response.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return text;
  }
}

showLogin.addEventListener('click', () => switchAuth('login'));
showSignup.addEventListener('click', () => switchAuth('signup'));

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  authMessage.textContent = '';
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value.trim();
  try {
    const response = await fetch('/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await parseResponse(response);
    if (!response.ok) {
      const message = data?.detail || data?.message || data || response.statusText;
      throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
    }
    token = data.access_token;
    currentRole = data.role;
    localStorage.setItem('ttm_token', token);
    localStorage.setItem('ttm_role', currentRole);
    localStorage.setItem('ttm_email', email);
    await loadDashboard();
  } catch (error) {
    authMessage.textContent = error.message;
  }
});

signupForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  authMessage.textContent = '';
  const username = document.getElementById('signup-username').value.trim();
  const email = document.getElementById('signup-email').value.trim();
  const password = document.getElementById('signup-password').value.trim();
  try {
    const response = await fetch('/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });
    const data = await parseResponse(response);
    if (!response.ok) {
      const message = data?.detail || data?.message || data || 'Signup failed';
      throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
    }
    authMessage.textContent = 'Signup complete. Please login.';
    switchAuth('login');
  } catch (error) {
    authMessage.textContent = error.message;
  }
});

logoutBtn.addEventListener('click', () => {
  localStorage.removeItem('ttm_token');
  localStorage.removeItem('ttm_role');
  localStorage.removeItem('ttm_email');
  token = null;
  currentRole = null;
  authSection.classList.remove('hidden');
  dashboard.classList.add('hidden');
});

async function loadDashboard() {
  if (!token) {
    token = localStorage.getItem('ttm_token');
    currentRole = localStorage.getItem('ttm_role');
  }
  if (!token) return;
  authSection.classList.add('hidden');
  dashboard.classList.remove('hidden');
  welcomeText.textContent = `Welcome back!`;
  roleText.textContent = `Role: ${currentRole}`;
  adminPanel.classList.toggle('hidden', currentRole !== 'Admin');
  await Promise.all([loadProjects(), loadTasks()]);
}

function switchAuth(mode) {
  if (mode === 'login') {
    showLogin.classList.add('active');
    showSignup.classList.remove('active');
    loginForm.classList.remove('hidden');
    signupForm.classList.add('hidden');
  } else {
    showSignup.classList.add('active');
    showLogin.classList.remove('active');
    signupForm.classList.remove('hidden');
    loginForm.classList.add('hidden');
  }
}

async function loadProjects() {
  projectList.innerHTML = '<p>Loading projects...</p>';
  try {
    const response = await fetch('/projects', {
      headers: { Authorization: `Bearer ${token}` },
    });
    const projects = await parseResponse(response);
    if (!response.ok) {
      const message = projects?.detail || projects?.message || projects || 'Could not fetch projects';
      throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
    }
    if (!projects.length) {
      projectList.innerHTML = '<p>No projects found.</p>';
      return;
    }
    projectList.innerHTML = projects
      .map(
        (project) => `
          <div class="item-card">
            <h3>${project.name}</h3>
            <p>${project.description || 'No description provided.'}</p>
            <div class="status-chip"><span>Project ID ${project.id}</span></div>
          </div>
        `
      )
      .join('');
  } catch (error) {
    projectList.innerHTML = `<p>${error.message}</p>`;
  }
}

async function loadTasks() {
  taskList.innerHTML = '<p>Loading tasks...</p>';
  try {
    const response = await fetch('/tasks', {
      headers: { Authorization: `Bearer ${token}` },
    });
    const tasks = await parseResponse(response);
    if (!response.ok) {
      const message = tasks?.detail || tasks?.message || tasks || 'Could not fetch tasks';
      throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
    }
    if (!tasks.length) {
      taskList.innerHTML = '<p>No tasks assigned yet.</p>';
      return;
    }
    taskList.innerHTML = tasks
      .map((task) => {
        const due = task.due_date ? new Date(task.due_date) : null;
        const overdue = due && new Date() > due && task.status !== 'Completed';
        const statusClass = task.status.toLowerCase().replace(' ', '-');
        const updateButton = currentRole === 'Admin' || task.assignee?.email === localStorage.getItem('ttm_email')
          ? `<button onclick="updateTaskStatus(${task.id}, '${nextStatus(task.status)}')">Move to ${nextStatus(task.status)}</button>`
          : '';
        return `
          <div class="item-card ${overdue ? 'task-overdue' : ''}">
            <h3>${task.title}</h3>
            <p>${task.description || 'No description'}</p>
            <p>Project #${task.project_id}</p>
            <p>Assigned: ${task.assignee?.username || 'Unassigned'}</p>
            <p>Due: ${due ? due.toLocaleDateString() : 'Not set'}</p>
            <div class="status-chip">
              <span class="status-${statusClass}">${task.status}</span>
              ${overdue ? '<span style="color:#dc2626;">Overdue</span>' : ''}
            </div>
            ${updateButton}
          </div>
        `;
      })
      .join('');
  } catch (error) {
    taskList.innerHTML = `<p>${error.message}</p>`;
  }
}

function nextStatus(status) {
  if (status === 'Pending') return 'In Progress';
  if (status === 'In Progress') return 'Completed';
  return 'Completed';
}

window.updateTaskStatus = async (taskId, status) => {
  try {
    const response = await fetch(`/tasks/${taskId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ status }),
    });
    const data = await parseResponse(response);
    if (!response.ok) {
      const message = data?.detail || data?.message || data || 'Could not update task';
      throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
    }
    await loadTasks();
  } catch (error) {
    alert(error.message);
  }
};

const createProjectForm = document.getElementById('create-project-form');
createProjectForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  projectMessage.textContent = '';
  try {
    const response = await fetch('/projects', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: document.getElementById('project-name').value.trim(),
        description: document.getElementById('project-description').value.trim(),
      }),
    });
    const data = await parseResponse(response);
    if (!response.ok) {
      const message = data?.detail || data?.message || data || 'Could not create project';
      throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
    }
    projectMessage.textContent = 'Project created successfully.';
    createProjectForm.reset();
    await loadProjects();
  } catch (error) {
    projectMessage.textContent = error.message;
  }
});

const createTaskForm = document.getElementById('create-task-form');
createTaskForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  taskMessage.textContent = '';
  try {
    const response = await fetch('/tasks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title: document.getElementById('task-title').value.trim(),
        description: document.getElementById('task-description').value.trim(),
        due_date: document.getElementById('task-due-date').value || null,
        project_id: Number(document.getElementById('task-project-id').value),
        assigned_to_email: document.getElementById('task-assignee-email').value.trim(),
      }),
    });
    const data = await parseResponse(response);
    if (!response.ok) {
      const message = data?.detail || data?.message || data || 'Could not create task';
      throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
    }
    taskMessage.textContent = 'Task created successfully.';
    createTaskForm.reset();
    await loadTasks();
  } catch (error) {
    taskMessage.textContent = error.message;
  }
});

const addMemberForm = document.getElementById('add-member-form');
addMemberForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  memberMessage.textContent = '';
  try {
    const projectId = Number(document.getElementById('member-project-id').value);
    const email = document.getElementById('member-email').value.trim();
    const response = await fetch(`/projects/${projectId}/members`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ email }),
    });
    const data = await parseResponse(response);
    if (!response.ok) {
      const message = data?.detail || data?.message || data || 'Could not add member';
      throw new Error(typeof message === 'object' ? JSON.stringify(message) : message);
    }
    memberMessage.textContent = 'Member added to project.';
    addMemberForm.reset();
  } catch (error) {
    memberMessage.textContent = error.message;
  }
});

window.addEventListener('load', async () => {
  token = localStorage.getItem('ttm_token');
  currentRole = localStorage.getItem('ttm_role');
  if (token) await loadDashboard();
});
