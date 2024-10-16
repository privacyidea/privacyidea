import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {LoginComponent} from './components/login/login.component';
import {TokenComponent} from './components/token/token.component';
import {AuthGuard} from './guards/auth.guard';

export const routes: Routes = [
  {path: '', component: LoginComponent},
  {path: 'token', component: TokenComponent, canActivate: [AuthGuard]},
  {path: '**', redirectTo: ''}
];


@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {
  constructor() {}
}
