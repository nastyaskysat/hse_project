const progressBar = document.getElementById('progressBar');
const output = document.getElementById('output');
const TEST_URL = 'https://cors-anywhere.herokuapp.com/https://www.gutenberg.org/files/1342/1342-0.txt';

//  Загрузка через XMLHttpRequest
function downloadWithXHR() {
  const xhr = new XMLHttpRequest();
  xhr.open('GET', TEST_URL, true);
  xhr.responseType = 'text';

  xhr.onprogress = function (event) {
    if (event.lengthComputable) {
      const percent = (event.loaded / event.total) * 100;
      updateProgressBar(percent);
    }
  };

  xhr.onload = function () {
    if (xhr.status === 200) {
      updateProgressBar(100);
      output.textContent = xhr.responseText.slice(0, 1000) + '\n...';
    } else {
      output.textContent = 'Ошибка загрузки: ' + xhr.status;
    }
  };

  xhr.onerror = function () {
    output.textContent = 'Ошибка сети при загрузке.';
  };

  xhr.send();
}

//  Загрузка через Fetch + ReadableStream
async function downloadWithFetch() {
  const response = await fetch(TEST_URL);
  if (!response.ok) {
    output.textContent = `Ошибка загрузки: ${response.status}`;
    return;
  }

  const contentLength = response.headers.get('Content-Length');
  if (!contentLength) {
    output.textContent = 'Не удалось определить размер файла.';
    return;
  }

  const reader = response.body.getReader();
  const total = +contentLength;
  let received = 0;
  let chunks = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    chunks.push(value);
    received += value.length;
    const percent = (received / total) * 100;
    updateProgressBar(percent);
  }

  const decoder = new TextDecoder('utf-8');
  const text = decoder.decode(new Uint8Array(chunks.flat()));
  output.textContent = text.slice(0, 1000) + '\n...';
}

//  Обновление прогресс-бара
function updateProgressBar(percent) {
  progressBar.style.width = percent.toFixed(1) + '%';
}

