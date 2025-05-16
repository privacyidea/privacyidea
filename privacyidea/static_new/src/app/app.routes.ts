import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './components/login/login.component';
import { TokenComponent } from './components/token/token.component';
import { adminMatch, AuthGuard, selfServiceMatch } from './guards/auth.guard';
import { LayoutComponent } from './components/layout/layout.component';
import { TokenSelfServiceComponent } from './components/token/token.self-service.component';
import { UserComponent } from './components/user/user.component';
import { UserSelfServiceComponent } from './components/user/user.self-service.component';
import { AuditComponent } from './components/audit/audit.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    component: LayoutComponent,
    children: [
      {
        path: 'token',
        canMatch: [adminMatch],
        canActivate: [AuthGuard],
        component: TokenComponent,
      },
      {
        path: 'token',
        canMatch: [selfServiceMatch],
        canActivate: [AuthGuard],
        component: TokenSelfServiceComponent,
      },
      {
        path: 'user',
        canMatch: [adminMatch],
        canActivate: [AuthGuard],
        component: UserComponent,
      },
      {
        path: 'user',
        canMatch: [selfServiceMatch],
        canActivate: [AuthGuard],
        component: UserSelfServiceComponent,
      },
      {
        path: 'audit',
        canActivate: [AuthGuard],
        component: AuditComponent,
      },
      { path: '', redirectTo: '/login', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: '/login' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: false })],
  exports: [RouterModule],
})
export class AppRoutingModule {}
