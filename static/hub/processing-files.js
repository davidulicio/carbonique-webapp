// GitHub is the current source for processing settings.
export function createProcessingFiles() {
  function view(){
    return `<section class="panel processing-source"><div class="panel-title"><h2>TraceAnalysis INI files</h2></div><p>Current processing files are maintained in the Carbonique software and settings repository. Open the folder on GitHub to view the latest files, download them, or inspect their commit history.</p><a class="button primary" href="https://github.com/CARBONI-QUE/UQAM_Software_and_Settings/tree/main/Database/Calculation_Procedures/TraceAnalysis_ini" target="_blank" rel="noopener noreferrer">Open INI files on GitHub ↗</a><p class="small muted">An internet connection is required. Historical configuration evidence linked to caveats remains in the records below.</p></section>`;
  }
  return {view,action:async()=>false};
}
