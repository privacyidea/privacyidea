import { Routes } from "@angular/router";
import { ChallengesTableComponent } from "./components/token/challenges-table/challenges-table.component";
import { ContainerCreateComponent } from "./components/token/container-create/container-create.component";
import { ContainerDetailsComponent } from "./components/token/container-details/container-details.component";
import { ContainerTableComponent } from "./components/token/container-table/container-table.component";
import { TokenApplicationsComponent } from "./components/token/token-applications/token-applications.component";
import { TokenDetailsComponent } from "./components/token/token-details/token-details.component";
import { TokenEnrollmentComponent } from "./components/token/token-enrollment/token-enrollment.component";
import { TokenGetSerialComponent } from "./components/token/token-get-serial/token-get-serial.component";
import { TokenTableComponent } from "./components/token/token-table/token-table.component";
import { TokenComponent } from "./components/token/token.component";
import { UserDetailsComponent } from "./components/user/user-details/user-details.component";
import { UserTableComponent } from "./components/user/user-table/user-table.component";
import { UserComponent } from "./components/user/user.component";
import { AuditComponent } from "./components/audit/audit.component";

export const routes: Routes = [
  {
    path: "tokens",
    component: TokenComponent,
    children: [
      { path: "", component: TokenTableComponent },
      { path: "enrollment", component: TokenEnrollmentComponent },
      { path: "challenges", component: ChallengesTableComponent },
      { path: "applications", component: TokenApplicationsComponent },
      { path: "get-serial", component: TokenGetSerialComponent },
      {
        path: "containers",
        children: [
          { path: "", component: ContainerTableComponent },
          { path: "create", component: ContainerCreateComponent },
          { path: "details/:serial", component: ContainerDetailsComponent }
        ]
      },
      { path: "details/:serial", component: TokenDetailsComponent }
    ]
  },
  {
    path: "users",
    component: UserComponent,
    children: [
      { path: "", component: UserTableComponent },
      { path: "details/:username", component: UserDetailsComponent }
    ]
  },
  {
    path: "audit",
    component: AuditComponent
  }
];
