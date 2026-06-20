const el = (id) => document.getElementById(id);
    let csrfToken = '';
    function showError(msg){ el('adminError').textContent = msg; el('adminError').classList.remove('hidden'); }
    function hideError(){ el('adminError').textContent = ''; el('adminError').classList.add('hidden'); }
    async function init(){
      const me = await fetch('/api/me').then(r => r.json());
      csrfToken = me.csrf_token;
      await loadConfig();
    }
    async function loadConfig(){
      hideError();
      const res = await fetch('/api/config', { headers: { 'X-CSRF-Token': csrfToken } });
      const data = await res.json();
      if(!res.ok){ showError(data.detail || 'Unable to load config'); return; }
      el('brandTagline').value = data.brand_tagline || 'Shockingly Accurate';
      const logoUrl = data.brand_logo?.url || '/brand/logo';
      el('logoPreview').src = logoUrl + (logoUrl.includes('?') ? '&' : '?') + 'preview=' + Date.now();
      el('freePlan').value = data.pricing?.free || 'Summary';
      el('premiumPlan').value = data.pricing?.premium || '₹99 Full Report';
      el('compatPlan').value = data.pricing?.compatibility || '₹149 Couple Report';
      el('demoDataVisible').checked = Boolean(data.features?.demo_data_button);
      el('configPreview').textContent = JSON.stringify(data, null, 2);
    }
    async function saveConfig(){
      hideError();
      const payload = {
        brand_tagline: el('brandTagline').value || 'Shockingly Accurate',
        pricing: {
          free: el('freePlan').value || 'Summary',
          premium: el('premiumPlan').value || '₹99 Full Report',
          compatibility: el('compatPlan').value || '₹149 Couple Report'
        },
        features: {
          pdf: true,
          whatsapp: true,
          history: true,
          compatibility: true,
          story_cards: true,
          demo_data_button: el('demoDataVisible').checked
        }
      };
      const res = await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: JSON.stringify(payload) });
      const data = await res.json();
      if(!res.ok){ showError(data.detail || 'Unable to save config'); return; }
      el('configPreview').textContent = JSON.stringify(data, null, 2);
    }
    function readFileAsDataUrl(file){
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error('Unable to read selected logo file.'));
        reader.readAsDataURL(file);
      });
    }
    async function uploadLogo(){
      hideError();
      const file = el('logoFile').files && el('logoFile').files[0];
      if(!file){ showError('Please choose a logo image first.'); return; }
      if(file.size > 3500000){ showError('Logo is too large. Please select an image under 3.5 MB.'); return; }
      const btn = el('uploadLogoBtn');
      btn.disabled = true; btn.textContent = 'Uploading...';
      try{
        const logo_data_url = await readFileAsDataUrl(file);
        const res = await fetch('/api/admin/logo', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: JSON.stringify({ logo_data_url }) });
        const data = await res.json();
        if(!res.ok){ throw new Error(data.detail || 'Unable to upload logo'); }
        el('logoFile').value = '';
        el('configPreview').textContent = JSON.stringify(data, null, 2);
        const logoUrl = data.brand_logo?.url || '/brand/logo';
        el('logoPreview').src = logoUrl + (logoUrl.includes('?') ? '&' : '?') + 'preview=' + Date.now();
      }catch(err){ showError(err.message || 'Unable to upload logo'); }
      finally{ btn.disabled = false; btn.textContent = 'Upload Logo'; }
    }
    async function resetLogo(){
      hideError();
      if(!confirm('Reset to the default Life Path Decoder logo?')) return;
      const res = await fetch('/api/admin/logo', { method: 'DELETE', headers: { 'X-CSRF-Token': csrfToken } });
      const data = await res.json();
      if(!res.ok){ showError(data.detail || 'Unable to reset logo'); return; }
      el('configPreview').textContent = JSON.stringify(data, null, 2);
      el('logoPreview').src = '/brand/logo?preview=' + Date.now();
    }
    el('loadConfigBtn').addEventListener('click', loadConfig);
    el('saveConfigBtn').addEventListener('click', saveConfig);
    el('uploadLogoBtn').addEventListener('click', uploadLogo);
    el('resetLogoBtn').addEventListener('click', resetLogo);
    init().catch(err => showError(err.message || 'Unable to start admin'));
