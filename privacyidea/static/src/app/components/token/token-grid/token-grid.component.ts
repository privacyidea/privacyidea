import {Component} from '@angular/core';
import {TokenTableComponent} from '../token-table/token-table.component';
import {CommonModule} from '@angular/common';

@Component({
  selector: 'app-token-grid',
  standalone: true,
  imports: [
    CommonModule,
    TokenTableComponent,
  ],
  templateUrl: './token-grid.component.html',
  styleUrl: './token-grid.component.css'
})
export class TokenGridComponent {
  ngOnInit(): void {
    console.log('TokenGridComponent initialized');
  }
}
