import {Component, Input, WritableSignal} from '@angular/core';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton} from '@angular/material/button';
import {animate, state, style, transition, trigger} from '@angular/animations';
import {NgClass} from '@angular/common';

@Component({
  selector: 'app-container-tab',
  standalone: true,
  imports: [
    MatIcon,
    MatList,
    MatListItem,
    MatButton,
    NgClass
  ],
  templateUrl: './container-tab.component.html',
  styleUrl: './container-tab.component.scss',
  animations: [
    trigger('toggleState', [
      state('false', style({
        transform: 'translateY(0)'
      })),
      state('true', style({
        transform: 'translateY(0)'
      })),
      transition('false => true', [
        style({
          transform: 'translateY(50%)'
        }),
        animate('200ms ease-in', style({
          transform: 'translateY(0)'
        }))
      ]),
      transition('true => false', [
        style({
          transform: 'translateY(50%)'
        }),
        animate('200ms ease-out', style({
          transform: 'translateY(0)'
        }))
      ])
    ])
  ]
})
export class ContainerTabComponent {
  @Input() containerIsSelected!: WritableSignal<boolean>;
}
