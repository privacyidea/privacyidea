import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './components/login/login.component';
import { LayoutComponent } from './components/layout/layout.component';
import { AuditComponent } from './components/audit/audit.component';
import { adminMatch, AuthGuard, selfServiceMatch } from './guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    component: LayoutComponent,
    canActivateChild: [AuthGuard],
    children: [
      {
        path: 'tokens',
        canMatch: [adminMatch],
        loadChildren: () => import('./admin.routes').then((m) => m.routes),
      },
      {
        path: 'tokens',
        canMatch: [selfServiceMatch],
        loadChildren: () =>
          import('./self-service.routes').then((m) => m.routes),
      },
      {
        path: 'users',
        canMatch: [adminMatch],
        loadChildren: () => import('./admin.routes').then((m) => m.routes),
      },
      {
        path: 'users',
        canMatch: [selfServiceMatch],
        loadChildren: () =>
          import('./self-service.routes').then((m) => m.routes),
      },

      { path: 'audit', component: AuditComponent },
      { path: '', redirectTo: 'tokens', pathMatch: 'full' },
    ],
  },
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: '**', redirectTo: '/login' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: false })],
  exports: [RouterModule],
})
export class AppRoutingModule {}
