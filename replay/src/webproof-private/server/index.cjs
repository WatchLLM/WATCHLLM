'use strict';
const { app } = require('../../server/index.cjs');
const { db, dbPath } = require('../../server/db.cjs');
const { createProofExtension } = require('./proofs.cjs');
const extension = createProofExtension({ db });
extension.mount(app);
if (require.main === module) {
  const port = Number(process.env.PORT || 3001);
  app.listen(port, () => {
    console.log(`WatchLLM Replay WebProof dashboard listening on http://localhost:${port}`);
    console.log(`SQLite projection initialised at ${dbPath}`);
  });
}
module.exports = { app, extension };
