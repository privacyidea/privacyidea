import {Component} from '@angular/core';
import {CommonModule} from '@angular/common';
import {MatSidenavModule} from '@angular/material/sidenav';

@Component({
  selector: 'app-token-get-serial',
  standalone: true,
  imports: [
    CommonModule,
    MatSidenavModule
],
  templateUrl: './token-get-serial.component.html',
  styleUrl: './token-get-serial.component.scss'
})
export class TokenIdentifySerialComponent {


  constructor( ) { }
}
