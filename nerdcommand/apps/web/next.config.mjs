/**
 * Next.js config for the JARVIS web UI.
 *
 * The browser never talks to the backend directly. All `/api/*` requests use
 * relative URLs, and the Next.js dev server rewrites them to the FastAPI
 * service. `NEXT_PUBLIC_JARVIS_API` can point at a remote API URL if the
 * frontend and backend are served from different origins in production.
 */
const apiTarget = process.env.NEXT_PUBLIC_JARVIS_API || "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
