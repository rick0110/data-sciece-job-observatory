(function () {
        const KEY = 'jobobs-dark-mode'; 
        const switchElement = document.getElementById('darkModeSwitch');
        const htmlEl = document.documentElement;

        function applyDark(isDark) {
          htmlEl.classList.toggle('dark', !!isDark);
          if (switchElement) switchElement.checked = !!isDark;
        }
        try {
          const saved = localStorage.getItem(KEY);
          if (saved === '1' || saved === '0') {
            applyDark(saved === '1');
          } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            applyDark(true);
          } else {
            applyDark(false);
          }
        } catch (e) {
        }

        if (switchElement) {
          switchElement.addEventListener('change', () => {
            const isDark = !!switchElement.checked;
            applyDark(isDark);
            try { localStorage.setItem(KEY, isDark ? '1' : '0'); } catch (e) {}
          });
        }
      })();