let serviceRows=[];
let serviceSearchTerm='';
let selectedService=null;

function setServiceMessage(message,isError=false){
    const target=$('#serviceMessage');
    if(!target)return;
    target.textContent=message;
    target.className=message?`alert ${isError?'danger':'success'}`:'';
}

async function servicesPage(search=serviceSearchTerm,notice=''){
    serviceSearchTerm=search;
    const query=search?`?search=${encodeURIComponent(search)}`:'';
    serviceRows=await api('/api/services'+query);
    const canManage=me.role==='admin';
    const editing=selectedService;
    const form=canManage?`<div class="panel"><h3>${editing?'Sửa dịch vụ':'Thêm dịch vụ'}</h3><form id="serviceForm" class="form-grid"><input name="name" maxlength="150" placeholder="Tên dịch vụ" value="${esc(editing?.name)}" required><input name="price" type="number" min="0" step="0.01" placeholder="Giá" value="${editing?.price??''}" required><input name="duration_minutes" type="number" min="1" step="1" placeholder="Thời lượng (phút)" value="${editing?.duration_minutes??''}" required><select name="status"><option value="active" ${!editing||editing.status==='active'?'selected':''}>Đang hoạt động</option><option value="inactive" ${editing?.status==='inactive'?'selected':''}>Ngừng hoạt động</option></select><textarea class="full" name="description" placeholder="Mô tả dịch vụ">${esc(editing?.description)}</textarea><div class="actions full"><button>${editing?'Lưu thay đổi':'Thêm dịch vụ'}</button>${editing?'<button type="button" class="secondary" onclick="cancelServiceEdit()">Hủy sửa</button>':''}</div></form></div>`:'';
    shell('Quản lý dịch vụ',`${form}<div id="serviceMessage" class="${notice?'alert success':''}">${esc(notice)}</div><div class="panel"><h3>Danh sách dịch vụ</h3><form id="serviceSearch" class="actions"><input id="serviceSearchInput" value="${esc(search)}" placeholder="Tìm dịch vụ theo tên"><button>Tìm kiếm</button></form><div class="table-wrap"><table><thead><tr><th>Tên</th><th>Mô tả</th><th>Giá</th><th>Thời lượng</th><th>Trạng thái</th>${canManage?'<th>Thao tác</th>':''}</tr></thead><tbody>${serviceRows.map(service=>`<tr><td><b>${esc(service.name)}</b></td><td>${esc(service.description||'')}</td><td>${Number(service.price).toLocaleString('vi-VN')} đ</td><td>${service.duration_minutes} phút</td><td><span class="badge ${service.status==='active'?'success':'warning'}">${service.status==='active'?'Đang hoạt động':'Ngừng hoạt động'}</span></td>${canManage?`<td class="actions"><button onclick="editService(${service.id})">Sửa</button><button class="danger-btn" onclick="removeService(${service.id})">Xóa</button></td>`:''}</tr>`).join('')}</tbody></table></div>${serviceRows.length?'':'<p class="empty">Không tìm thấy dịch vụ.</p>'}</div>`);
    $('#serviceSearch').onsubmit=async e=>{
        e.preventDefault();
        selectedService=null;
        try{await servicesPage($('#serviceSearchInput').value.trim())}
        catch(error){if(error.unauthorized)return;setServiceMessage(error.message,true)}
    };
    const serviceFormElement=$('#serviceForm');
    if(serviceFormElement)serviceFormElement.onsubmit=async e=>{
        e.preventDefault();
        const values=Object.fromEntries(new FormData(e.target));
        values.name=values.name.trim();
        values.price=Number(values.price);
        values.duration_minutes=Number(values.duration_minutes);
        try{
            if(selectedService){
                await api('/api/services/'+selectedService.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});
                selectedService=null;
                await servicesPage(serviceSearchTerm,'Dịch vụ đã được cập nhật.');
            }else{
                await api('/api/services',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});
                await servicesPage(serviceSearchTerm,'Dịch vụ đã được thêm.');
            }
        }catch(error){if(error.unauthorized)return;setServiceMessage(error.message,true)}
    };
}

window.editService=async id=>{
    selectedService=serviceRows.find(service=>service.id===id)||null;
    try{await servicesPage(serviceSearchTerm)}
    catch(error){if(error.unauthorized)return;setServiceMessage(error.message,true)}
};

window.cancelServiceEdit=async()=>{
    selectedService=null;
    try{await servicesPage(serviceSearchTerm)}
    catch(error){if(error.unauthorized)return;setServiceMessage(error.message,true)}
};

window.removeService=async id=>{
    const service=serviceRows.find(item=>item.id===id);
    if(!service||!confirm(`Xóa dịch vụ "${service.name}"? Dịch vụ đang được lịch chăm sóc sử dụng sẽ được chuyển sang ngừng hoạt động.`))return;
    try{
        const result=await api('/api/services/'+id,{method:'DELETE'});
        await servicesPage(serviceSearchTerm,result.message);
    }catch(error){if(error.unauthorized)return;setServiceMessage(error.message,true)}
};

async function schedulePageWithServices(){
    await schedulePage();
    const form=$('#schForm');
    if(!form)return;
    const [availableServices,schedules]=await Promise.all([api('/api/services'),api('/api/schedules')]);
    const services=availableServices.filter(service=>service.status==='active');
    const select=document.createElement('select');
    select.name='service_picker';
    const placeholder=document.createElement('option');
    placeholder.value='';
    placeholder.textContent='Không gắn dịch vụ';
    select.appendChild(placeholder);
    for(const service of services){
        const option=document.createElement('option');
        option.value=String(service.id);
        option.textContent=`${service.name} · ${Number(service.price).toLocaleString('vi-VN')} đ`;
        select.appendChild(option);
    }
    form.querySelector('[name="scheduled_date"]').before(select);
    const scheduleTable=$('#content table');
    if(scheduleTable){
        const header=scheduleTable.tHead.rows[0].insertCell(2);
        header.outerHTML='<th>Dịch vụ</th>';
        Array.from(scheduleTable.tBodies[0].rows).forEach((row,index)=>{
            const cell=row.insertCell(2);
            cell.textContent=schedules[index]?.service_name||'—';
            const actions=row.cells[row.cells.length-1];
            const reminderButton=document.createElement('button');
            reminderButton.type='button';
            reminderButton.textContent='Tạo nhắc AI';
            reminderButton.onclick=()=>window.generateScheduleReminder(schedules[index].id);
            actions.appendChild(reminderButton);
        });
        const output=document.createElement('div');
        output.id='aiReminderOutput';
        output.className='panel hidden';
        output.setAttribute('role','status');
        output.setAttribute('aria-live','polite');
        output.style.whiteSpace='pre-wrap';
        output.textContent='Nội dung nhắc lịch AI chỉ hỗ trợ quản lý lịch, không thay thế tư vấn thú y.';
        $('#content').appendChild(output);
    }
    form.addEventListener('submit',event=>{
        let serviceIdInput=form.querySelector('[name="service_id"]');
        if(select.value){
            if(!serviceIdInput){
                serviceIdInput=document.createElement('input');
                serviceIdInput.type='hidden';
                serviceIdInput.name='service_id';
                form.appendChild(serviceIdInput);
            }
            serviceIdInput.value=select.value;
        }else if(serviceIdInput){
            serviceIdInput.remove();
        }
    },true);
}

window.generateScheduleReminder=async scheduleId=>{
    const output=$('#aiReminderOutput');
    if(!output)return;
    output.classList.remove('hidden','danger');
    output.classList.add('alert');
    output.textContent='Đang tạo nội dung nhắc lịch…';
    try{
        const result=await api('/api/ai/reminder/'+scheduleId,{method:'POST'});
        output.textContent=`Nguồn: ${result.source}\n${result.message}\n\nAI hỗ trợ quản lý lịch, không thay thế tư vấn thú y.`;
    }catch(error){
        if(error.unauthorized)return;
        output.classList.add('danger');
        output.textContent=`Không thể tạo nội dung nhắc lịch: ${error.message}`;
    }
};
