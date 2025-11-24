document.addEventListener('DOMContentLoaded', function() {

const demoData = {
    cargo: "Data Scientist Junior",
    salario: "5500.00",
    desc: "Experiência com Python, Pandas e Scikit-Learn. Vaga para atuar em projetos de NLP."
};

const fields = {
    cargo: document.getElementById('anim-cargo'),
    salario: document.getElementById('anim-salario'),
    desc: document.getElementById('anim-desc'),
    btn: document.getElementById('anim-btn'),
    success: document.getElementById('anim-success')
};

function typeText(element, text, speed = 50) {
    return new Promise(resolve => {
      element.value = "";
      element.classList.add('typing-active'); 
      let i = 0;
      
      function type() {
        if (i < text.length) {
          element.value += text.charAt(i);
          i++;
          setTimeout(type, speed + Math.random() * 70); 
        } else {
          element.classList.remove('typing-active');
          resolve();
        }
      }
      type();
    });
  }

  async function runAnimation() {
    fields.cargo.value = "";
    fields.salario.value = "";
    fields.desc.value = "";
    fields.success.style.opacity = "0";
    fields.btn.classList.remove('btn-success');
    fields.btn.innerHTML = "Enviar Vaga";
    
    await new Promise(r => setTimeout(r, 1000));

    await typeText(fields.cargo, demoData.cargo, 60);
    
    await typeText(fields.salario, demoData.salario, 80);

    await typeText(fields.desc, demoData.desc, 30);

    await new Promise(r => setTimeout(r, 500));
    fields.btn.classList.add('active');
    fields.btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Enviando...';
    
    await new Promise(r => setTimeout(r, 1500)); // Tempo de "processamento"

    fields.success.style.opacity = "1";
    
    setTimeout(runAnimation, 4000);
  }

if(document.getElementById('anim-cargo')) {
    runAnimation();
  }
});