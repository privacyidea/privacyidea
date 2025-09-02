import { NgModule } from "@angular/core";
import { RouterModule, Routes } from "@angular/router";
import { LayoutComponent } from "./components/layout/layout.component";
import { LoginComponent } from "./components/login/login.component";
import { adminMatch, AuthGuard, selfServiceMatch } from "./guards/auth.guard";

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
        loadChildren: () => import("./self-service.routes").then((m) => m.routes)
      }
    ]
  },
  { path: "**", redirectTo: "login" }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: false })],
  exports: [RouterModule]
})
export class AppRoutingModule {}
