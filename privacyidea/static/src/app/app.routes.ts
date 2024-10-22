import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {LoginComponent} from './components/login/login.component';
import {TokenGridComponent} from './components/token/token-grid/token-grid.component';
import {GridLayoutComponent} from './components/grid-layout/grid-layout.component';
import {AuthGuard} from './guards/auth.guard';

export const routes: Routes = [
  {path: 'login', component: LoginComponent},
  {
    path: '',
    component: GridLayoutComponent,
    children: [
      {path: 'token', component: TokenGridComponent, canActivate: [AuthGuard]},
      {path: '', redirectTo: '/login', pathMatch: 'full'},
    ]
  },
  {path: '**', redirectTo: '/login'}
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {useHash: false})],
  exports: [RouterModule],
})
export class AppRoutingModule {
}
