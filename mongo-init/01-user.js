// Runs once, on an empty data volume only, authenticated as the root user
// (docker-entrypoint-initdb.d convention). Creates a least-privilege
// application user scoped to the LibreChat database only — LibreChat never
// gets root/admin credentials.
const appPassword = process.env.MONGO_APP_PASSWORD;
if (!appPassword) {
  throw new Error("MONGO_APP_PASSWORD is not set; aborting user creation");
}

db = db.getSiblingDB("LibreChat");
db.createUser({
  user: "librechat",
  pwd: appPassword,
  roles: [{ role: "readWrite", db: "LibreChat" }],
});
