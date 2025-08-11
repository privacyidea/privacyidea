import { Routes } from '@angular/router';

import { TokenSelfServiceComponent } from './components/token/token.self-service.component';
import { TokenTableSelfServiceComponent } from './components/token/token-table/token-table.self-service.component';
import { TokenEnrollmentSelfServiceComponent } from './components/token/token-enrollment/token-enrollment.self-service.component';
import { TokenDetailsSelfServiceComponent } from './components/token/token-details/token-details.self-service.component';
import { ContainerTableSelfServiceComponent } from './components/token/container-table/container-table.self-service.component';
import { ContainerCreateSelfServiceComponent } from './components/token/container-create/container-create.self-service.component';
import { ContainerDetailsSelfServiceComponent } from './components/token/container-details/container-details.self-service.component';
import { UserSelfServiceComponent } from './components/user/user.self-service.component';
import { AssignTokenSelfServiceComponent } from './components/token/assign-token-self-service/assign-token-self-service.component';

export const routes: Routes = [
  {
    path: 'tokens',
    component: TokenSelfServiceComponent,
    children: [
      {
        path: '',
        pathMatch: 'full',
        component: TokenTableSelfServiceComponent,
      },
      { path: 'enrollment', component: TokenEnrollmentSelfServiceComponent },
      { path: 'assign-token', component: AssignTokenSelfServiceComponent },
      {
        path: 'containers',
        children: [
          { path: '', component: ContainerTableSelfServiceComponent },
          { path: 'create', component: ContainerCreateSelfServiceComponent },
          {
            path: 'details/:serial',
            component: ContainerDetailsSelfServiceComponent,
          },
        ],
      },
      { path: 'details/:serial', component: TokenDetailsSelfServiceComponent },
    ],
  },
  {
    path: 'users',
    component: UserSelfServiceComponent,
  },
];
