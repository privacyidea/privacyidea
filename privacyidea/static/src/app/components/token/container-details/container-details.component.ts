import {Component, Input, WritableSignal} from '@angular/core';

@Component({
  selector: 'app-container-details',
  standalone: true,
  imports: [],
  templateUrl: './container-details.component.html',
  styleUrl: './container-details.component.css'
})
export class ContainerDetailsComponent {
  @Input() serial!: WritableSignal<string>;

}
