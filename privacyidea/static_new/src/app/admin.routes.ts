import { Routes } from '@angular/router';
import { TokenComponent } from './components/token/token.component';
import { TokenTableComponent } from './components/token/token-table/token-table.component';
import { TokenEnrollmentComponent } from './components/token/token-enrollment/token-enrollment.component';
import { TokenDetailsComponent } from './components/token/token-details/token-details.component';
import { ChallengesTableComponent } from './components/token/challenges-table/challenges-table.component';
import { TokenApplicationsComponent } from './components/token/token-applications/token-applications.component';
import { TokenGetSerialComponent } from './components/token/token-get-serial/token-get-serial.component';
import { ContainerTableComponent } from './components/token/container-table/container-table.component';
import { ContainerCreateComponent } from './components/token/container-create/container-create.component';
import { ContainerDetailsComponent } from './components/token/container-details/container-details.component';
import { UserComponent } from './components/user/user.component';

export const routes: Routes = [
  {
    path: 'tokens',
    component: TokenComponent,
    children: [
      { path: '', component: TokenTableComponent },
      { path: 'enroll', component: TokenEnrollmentComponent },
      { path: 'challenges', component: ChallengesTableComponent },
      { path: 'applications', component: TokenApplicationsComponent },
      { path: 'get-serial', component: TokenGetSerialComponent },
      {
        path: 'containers',
        children: [
          { path: '', component: ContainerTableComponent },
          { path: 'create', component: ContainerCreateComponent },
          { path: 'details/:serial', component: ContainerDetailsComponent },
        ],
      },
      { path: 'details/:serial', component: TokenDetailsComponent },
    ],
  },
  {
    path: 'users',
    component: UserComponent,
  },
];
