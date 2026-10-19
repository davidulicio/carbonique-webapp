/* Render original PDFs locally: no third-party document viewer or upload. */
export async function showPDF(container, data) {
  const pdfjs = await import("./vendor/pdfjs/pdf.mjs");
  pdfjs.GlobalWorkerOptions.workerSrc = new URL("./vendor/pdfjs/pdf.worker.mjs", import.meta.url).href;
  const document = await pdfjs.getDocument({data,standardFontDataUrl:new URL("./vendor/pdfjs/standard_fonts/",import.meta.url).href,isEvalSupported:false}).promise;
  let pageNumber=1;
  container.innerHTML='<div class="pdf-controls"><button type="button" class="button secondary small" data-pdf="previous">Previous page</button><span aria-live="polite" data-pdf="page"></span><button type="button" class="button secondary small" data-pdf="next">Next page</button></div><div class="pdf-canvas-wrap"><canvas aria-label="Protocol page"></canvas></div>';
  async function draw() {
    if(!container.isConnected)return;
    const previous=container.querySelector('[data-pdf="previous"]'),next=container.querySelector('[data-pdf="next"]');
    previous.disabled=next.disabled=true;
    const page=await document.getPage(pageNumber),canvas=container.querySelector("canvas"),base=page.getViewport({scale:1});
    const width=Math.min(1000,container.clientWidth-8),ratio=window.devicePixelRatio||1;
    const viewport=page.getViewport({scale:width/base.width});
    canvas.width=Math.floor(viewport.width*ratio);canvas.height=Math.floor(viewport.height*ratio);
    canvas.style.width=viewport.width+"px";canvas.style.height=viewport.height+"px";
    await page.render({canvasContext:canvas.getContext("2d"),viewport,transform:ratio===1?undefined:[ratio,0,0,ratio,0,0]}).promise;
    container.querySelector('[data-pdf="page"]').textContent=`Page ${pageNumber} of ${document.numPages}`;
    previous.disabled=pageNumber<=1;next.disabled=pageNumber>=document.numPages;
  }
  container.querySelector('[data-pdf="previous"]').onclick=()=>{pageNumber--;void draw();};
  container.querySelector('[data-pdf="next"]').onclick=()=>{pageNumber++;void draw();};
  await draw();
  return ()=>document.destroy();
}
