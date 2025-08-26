import { NgModule } from "@angular/core";
import { RouterModule, Routes } from "@angular/router";
import { LoginComponent } from "./components/login/login.component";
import { LayoutComponent } from "./components/layout/layout.component";
import { AuditComponent } from "./components/audit/audit.component";
import { adminMatch, AuthGuard, selfServiceMatch } from "./guards/auth.guard";

export const ROUTE_PATHS = {
  LOGIN: "/login",
  AUDIT: "/audit",
  TOKENS: "/tokens",
  USERS: "/users",
  TOKENS_DETAILS: "/tokens/details/",
  TOKENS_ENROLLMENT: "/tokens/enrollment",
  TOKENS_CHALLENGES: "/tokens/challenges",
  TOKENS_APPLICATIONS: "/tokens/applications",
  TOKENS_GET_SERIAL: "/tokens/get-serial",
  TOKENS_CONTAINERS: "/tokens/containers",
  TOKENS_CONTAINERS_CREATE: "/tokens/containers/create",
  TOKENS_CONTAINERS_DETAILS: "/tokens/containers/details/",
  TOKENS_ASSIGN_TOKEN: "/tokens/assign-token"
};

export const routes: Routes = [
  { path: "login", component: LoginComponent },
  { path: "", redirectTo: "login", pathMatch: "full" },
  {
    path: "",
    component: LayoutComponent,
    canActivateChild: [AuthGuard],
    children: [
      {
        path: "",
        canMatch: [adminMatch],
        loadChildren: () => import("./admin.routes").then((m) => m.routes)
      },
      {
        path: "",
        canMatch: [selfServiceMatch],
        loadChildren: () =>
          import("./self-service.routes").then((m) => m.routes)
      },
    ],
  },
  { path: "**", redirectTo: "login" }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: false })],
  exports: [RouterModule]
})
export class AppRoutingModule {
}
