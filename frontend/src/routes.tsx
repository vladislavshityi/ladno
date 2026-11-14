import { createBrowserRouter, Navigate } from "react-router-dom";
import { RouteError } from "@/components/route-error";
import { AppLayout } from "@/components/app-layout";
import {
  RequireAuth,
  RequireConsent,
} from "@/features/auth/components/protected-route";
import ConsentPage from "@/features/auth/pages/consent-page";
import HomeRoute from "@/features/auth/pages/home-route";
import IssuePage from "@/features/issues/pages/issue-page";
import IssuesPage from "@/features/issues/pages/issues-page";
import NewIssuePage from "@/features/issues/pages/new-issue-page";
import ConsentTextPage from "@/features/legal/pages/consent-text-page";
import PrivacyPage from "@/features/legal/pages/privacy-page";
import ProfilePage from "@/features/profile/pages/profile-page";
import CompanyPage from "@/features/ratings/pages/company-page";
import RatingsPage from "@/features/ratings/pages/ratings-page";
import ReceiptPage from "@/features/receipts/pages/receipt-page";
import ReceiptsPage from "@/features/receipts/pages/receipts-page";

export const router = createBrowserRouter([
  {
    errorElement: <RouteError />,
    children: [
      { path: "/", element: <HomeRoute /> },
      { path: "/legal/privacy", element: <PrivacyPage /> },
      { path: "/legal/consent", element: <ConsentTextPage /> },
      {
        // Aggregates only, no personal data: open without signing in.
        element: <AppLayout />,
        children: [
          { path: "/ratings", element: <RatingsPage /> },
          { path: "/ratings/:companyId", element: <CompanyPage /> },
          {
            path: "/map",
            lazy: async () => ({
              Component: (await import("@/features/map/pages/map-page"))
                .default,
            }),
          },
        ],
      },
      {
        element: <RequireAuth />,
        children: [
          { path: "/consent", element: <ConsentPage /> },
          {
            element: <RequireConsent />,
            children: [
              {
                element: <AppLayout />,
                children: [
                  { path: "/issues/new", element: <NewIssuePage /> },
                  { path: "/issues", element: <IssuesPage /> },
                  { path: "/issues/:id", element: <IssuePage /> },
                  { path: "/receipts", element: <ReceiptsPage /> },
                  { path: "/receipts/:id", element: <ReceiptPage /> },
                  {
                    path: "/assistant",
                    lazy: async () => ({
                      Component: (
                        await import("@/features/assistant/pages/assistant-route")
                      ).default,
                    }),
                  },
                  { path: "/profile", element: <ProfilePage /> },
                ],
              },
            ],
          },
        ],
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
